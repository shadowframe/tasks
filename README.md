# TaskLite Stack

A self-hosted TaskLite deployment with:

- TaskLite API and SQLite persistence
- a webapp built from a pinned public TaskLite downstream commit
- a small attachment service
- a Prometheus exporter

This repository is a deployment/customization project around [TaskLite](https://github.com/ad-si/TaskLite), not a replacement for the upstream project. The upstream source and license remain preserved in `TaskLite/` when that checkout is included.

## Public-repository boundary

The repository contains source code, Dockerfiles, Compose configuration, and safe configuration templates. It must not contain:

- `.env` or `versions.env`
- production databases or uploaded files
- private hostnames, Tailscale URLs, passwords, tokens, or signed URLs
- host-specific configuration files

Runtime state stays outside version control:

```text
data/
attachments/
.env
versions.env
```

Copy the templates before starting:

```bash
cp .env.example .env
cp versions.env.example versions.env
```

Then set deployment-specific values in those local files. `docker compose` reads `.env` automatically; `versions.env` is optional metadata and is not committed.

## Configuration

Important `.env` values:

- `TASKLITE_IMAGE` – TaskLite container image
- `TASKLITE_API_PORT` – local API bind port
- `TASKLITE_WEB_PORT` – local webapp bind port
- `TASKLITE_REF` – pinned public TaskLite commit used for the webapp build
- `TASKLITE_GRAPHQL_URL` – browser-reachable GraphQL URL
- `TASKLITE_CONFIG_FILE` – host path to the local TaskLite YAML configuration

The TaskLite YAML configuration may contain deployment-specific values such as the attachment-service URL. Keep it outside the repository, for example under `~/.config/tasklite/config.yaml`.

## Start and verify

```bash
docker compose up -d
docker compose ps
docker compose logs -f
```

Local endpoints depend on `.env`; the usual defaults are:

- API: `http://127.0.0.1:7458`
- Webapp: `http://127.0.0.1:3002`
- Attachment health: `http://127.0.0.1:3003/health`
- Exporter: internal Docker network, port `9460`

## Attachments

Attachments are stored below `attachments/<task-ulid>/` and referenced from TaskLite metadata. The directory contains user data and must remain local.

The attachment service currently provides upload, listing, download, and deletion endpoints. It is intended for a trusted self-hosted deployment and should be placed behind the deployment's authentication and network controls before exposing it outside the private network.

## Updating TaskLite

The webapp build uses the public downstream checkout in `TaskLite/` and a pinned `TASKLITE_REF`. Update the downstream checkout deliberately, test the stack, then update the local ref value. Do not commit a production hostname into `Dockerfile.webapp` or the Compose file.

The original project is available at:

- Repository: https://github.com/ad-si/TaskLite
- Downstream fork: https://github.com/shadowframe/TaskLite-hermes

## License and attribution

TaskLite remains subject to its upstream license and copyright notices. Any public release of this deployment repository should preserve those notices and add an explicit license for newly authored stack components before publication.
