#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

GRAPHQL_URL = os.environ.get("TASKLITE_GRAPHQL_URL", "http://tasklite:7458/graphql")
PORT = int(os.environ.get("TASKLITE_EXPORTER_PORT", "9460"))
ALLOWLIST = [
    tag.strip().lower()
    for tag in os.environ.get(
        "TASKLITE_TAG_ALLOWLIST",
        "homelab,hermes,arbeit,einkauf,kaufen,ideen",
    ).split(",")
    if tag.strip()
]
TIMEOUT = float(os.environ.get("TASKLITE_GRAPHQL_TIMEOUT", "10"))

QUERY = """
query TaskLiteMetrics {
  tasks_open(limit: 5000) {
    due_utc
  }
  tasks_overdue(limit: 5000) {
    ulid
  }
  tasks_done(limit: 5000) {
    ulid
  }
  tags(limit: 5000) {
    tag
    open
  }
}
""".strip()


def _http_query() -> dict:
    payload = json.dumps({"query": QUERY}).encode("utf-8")
    req = Request(
        GRAPHQL_URL,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=TIMEOUT) as resp:
        data = json.load(resp)
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def _escape_label(value: str) -> str:
    return value.replace("\\", r"\\").replace("\n", r"\n").replace('"', r'\"')


def build_metrics_text() -> str:
    data = _http_query()
    open_rows = data.get("tasks_open", [])
    overdue_rows = data.get("tasks_overdue", [])
    done_rows = data.get("tasks_done", [])
    tag_rows = data.get("tags", [])

    today = datetime.now(timezone.utc).date()
    due_today = sum(1 for row in open_rows if _parse_date(row.get("due_utc")) == today)

    tag_open = defaultdict(int)
    for row in tag_rows:
        tag = (row.get("tag") or "").strip().lower()
        if tag in ALLOWLIST:
            try:
                tag_open[tag] = int(row.get("open") or 0)
            except (TypeError, ValueError):
                tag_open[tag] = 0
    for tag in ALLOWLIST:
        tag_open.setdefault(tag, 0)

    lines = [
        "# HELP tasklite_tasks_open Current count of open TaskLite tasks.",
        "# TYPE tasklite_tasks_open gauge",
        f"tasklite_tasks_open {len(open_rows)}",
        "# HELP tasklite_tasks_due_today Current count of open tasks due today (UTC).",
        "# TYPE tasklite_tasks_due_today gauge",
        f"tasklite_tasks_due_today {due_today}",
        "# HELP tasklite_tasks_overdue Current count of overdue TaskLite tasks.",
        "# TYPE tasklite_tasks_overdue gauge",
        f"tasklite_tasks_overdue {len(overdue_rows)}",
        "# HELP tasklite_tasks_completed Current count of completed TaskLite tasks.",
        "# TYPE tasklite_tasks_completed gauge",
        f"tasklite_tasks_completed {len(done_rows)}",
        "# HELP tasklite_tasks_by_tag Current count of open tasks by allowed tag.",
        "# TYPE tasklite_tasks_by_tag gauge",
    ]
    for tag in ALLOWLIST:
        lines.append(
            f'tasklite_tasks_by_tag{{tag="{_escape_label(tag)}"}} {tag_open[tag]}'
        )
    lines.append("")
    return "\n".join(lines)


class Handler(BaseHTTPRequestHandler):
    server_version = "tasklite-exporter/1.0"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path not in ("/", "/metrics"):
            self.send_response(404)
            self.send_header("content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"not found\n")
            return

        if self.path == "/":
            body = (
                "tasklite exporter\n"
                f"metrics: http://127.0.0.1:{PORT}/metrics\n"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "text/plain; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        try:
            body = build_metrics_text().encode("utf-8")
        except (URLError, HTTPError, TimeoutError, RuntimeError, OSError) as exc:
            body = f"tasklite exporter error: {exc}\n".encode("utf-8")
            self.send_response(500)
            self.send_header("content-type", "text/plain; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        except Exception as exc:  # pragma: no cover - defensive
            body = f"tasklite exporter unexpected error: {exc}\n".encode("utf-8")
            self.send_response(500)
            self.send_header("content-type", "text/plain; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("content-type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
