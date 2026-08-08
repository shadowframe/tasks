import hashlib
import json
import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse

ATTACHMENTS_ROOT = Path(os.environ.get("ATTACHMENTS_ROOT", "/srv/attachments")).resolve()
GRAPHQL_URL = os.environ.get("TASKLITE_GRAPHQL_URL", "http://tasklite:7458/graphql")
MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))
ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")

app = FastAPI(title="TaskLite Attachments", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"] ,
)
ATTACHMENTS_ROOT.mkdir(parents=True, exist_ok=True)


def gql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    import urllib.request

    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.load(response)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TaskLite API unavailable: {exc}") from exc
    if result.get("errors"):
        raise HTTPException(status_code=502, detail=result["errors"])
    return result.get("data", {})


def validate_id(value: str) -> str:
    if not ID_RE.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid task or attachment id")
    return value


def resolve_task(task_id: str) -> dict[str, Any]:
    task_id = validate_id(task_id)
    comparison = {"eq": task_id} if len(task_id) >= 20 else {"ilike": f"%{task_id}"}
    data = gql(
        """
        query($filter: tasks_filter) {
          tasks(filter: $filter, limit: 3) {
            ulid
            body
            metadata
          }
        }
        """,
        {"filter": {"ulid": comparison}},
    )
    tasks = data.get("tasks", [])
    if not tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    if len(tasks) > 1:
        raise HTTPException(status_code=409, detail="Task id is ambiguous; use the full ULID")
    return tasks[0]


def parse_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"tasklite_metadata": raw}
    return value if isinstance(value, dict) else {"tasklite_metadata": value}


def save_metadata(task: dict[str, Any], metadata: dict[str, Any]) -> None:
    gql(
        """
        mutation($filter: tasks_filter!, $set: tasks_set_input!) {
          update_tasks(filter: $filter, set: $set) { affected_rows }
        }
        """,
        {
            "filter": {"ulid": {"eq": task["ulid"]}},
            "set": {"metadata": json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))},
        },
    )


def attachment_records(task: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = parse_metadata(task.get("metadata"))
    records = metadata.get("attachments", [])
    return records if isinstance(records, list) else []


def task_dir(task_ulid: str) -> Path:
    path = (ATTACHMENTS_ROOT / task_ulid).resolve()
    if ATTACHMENTS_ROOT not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid attachment path")
    path.mkdir(parents=True, exist_ok=True)
    return path


def record_path(record: dict[str, Any]) -> Path:
    attachment_id = validate_id(str(record.get("id", "")))
    task_ulid = validate_id(str(record.get("task_ulid", "")))
    path = (ATTACHMENTS_ROOT / task_ulid / f"{attachment_id}--{record.get('stored_name', '')}").resolve()
    if ATTACHMENTS_ROOT not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid attachment path")
    return path


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/tasks/{task_id}/attachments")
def list_attachments(task_id: str) -> dict[str, Any]:
    task = resolve_task(task_id)
    return {"task": task, "attachments": attachment_records(task)}


@app.post("/api/tasks/{task_id}/attachments", response_model=None)
def upload_attachment(request: Request, task_id: str, file: UploadFile = File(...)) -> JSONResponse | RedirectResponse:
    task = resolve_task(task_id)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    original_name = Path(file.filename).name
    if not original_name or original_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")
    attachment_id = uuid.uuid4().hex
    stored_name = re.sub(r"[^A-Za-z0-9._ -]", "_", original_name).strip()[:180] or "attachment"
    target = task_dir(task["ulid"]) / f"{attachment_id}--{stored_name}"
    digest = hashlib.sha256()
    total = 0
    try:
        with target.open("xb") as output:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_SIZE:
                    raise HTTPException(status_code=413, detail="Upload exceeds configured size limit")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    record = {
        "id": attachment_id,
        "task_ulid": task["ulid"],
        "name": original_name,
        "stored_name": stored_name,
        "mime": file.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream",
        "size": total,
        "sha256": digest.hexdigest(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    metadata = parse_metadata(task.get("metadata"))
    metadata.setdefault("attachments", [])
    if not isinstance(metadata["attachments"], list):
        metadata["attachments"] = []
    metadata["attachments"].append(record)
    try:
        save_metadata(task, metadata)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url=f"/tasks/{task['ulid']}", status_code=303)
    return JSONResponse(record, status_code=201)


@app.get("/api/attachments/{attachment_id}")
def download_attachment(attachment_id: str) -> StreamingResponse:
    attachment_id = validate_id(attachment_id)
    # The id is globally unique, so locate it without trusting a user-supplied path.
    matches = list(ATTACHMENTS_ROOT.glob(f"*/{attachment_id}--*"))
    if len(matches) != 1:
        raise HTTPException(status_code=404, detail="Attachment not found")
    path = matches[0]
    name = path.name.split("--", 1)[1]
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return StreamingResponse(path.open("rb"), media_type=mime, headers={"Content-Disposition": f'inline; filename="{name.replace(chr(34), "_")}"'})


@app.delete("/api/attachments/{attachment_id}")
def delete_attachment(attachment_id: str) -> dict[str, str]:
    attachment_id = validate_id(attachment_id)
    matches = list(ATTACHMENTS_ROOT.glob(f"*/{attachment_id}--*"))
    if len(matches) != 1:
        raise HTTPException(status_code=404, detail="Attachment not found")
    task_ulid = matches[0].parent.name
    task = resolve_task(task_ulid)
    metadata = parse_metadata(task.get("metadata"))
    metadata["attachments"] = [a for a in attachment_records(task) if str(a.get("id")) != attachment_id]
    save_metadata(task, metadata)
    matches[0].unlink()
    return {"status": "deleted"}


@app.get("/tasks/{task_id}", response_class=HTMLResponse)
def task_page(task_id: str) -> str:
    task = resolve_task(task_id)
    rows = []
    for record in attachment_records(task):
        attachment_id = str(record.get("id", ""))
        name = str(record.get("name", "attachment")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows.append(f'<li><a href="/api/attachments/{attachment_id}">{name}</a> ({record.get("size", 0)} bytes)</li>')
    body = "".join(rows) or "<li>No attachments yet.</li>"
    return f"""<!doctype html><meta charset='utf-8'><title>Attachments</title>
    <style>body{{font:16px system-ui;max-width: fiftyrem;max-width:50rem;margin:2rem auto;padding:0 1rem}}li{{margin:.6rem 0}}</style>
    <h1>Attachments for {task['ulid'][-5:]}</h1><p>{str(task.get('body','')).replace('<','&lt;')}</p>
    <form action='/api/tasks/{task['ulid']}/attachments' method='post' enctype='multipart/form-data'>
      <input type='file' name='file' required><button type='submit'>Upload</button>
    </form><h2>Files</h2><ul>{body}</ul>"""
