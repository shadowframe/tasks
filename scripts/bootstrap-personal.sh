#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CONFIG_FILE=${TASKLITE_CONFIG_FILE:-}
ATTACHMENTS_WEB_URL=${TASKLITE_ATTACHMENTS_PUBLIC_BASE:-}
DRY_RUN=false

usage() {
    cat <<'EOF'
Usage: ./scripts/bootstrap-personal.sh [--dry-run]

Create the optional personal Task-Stack configuration.

The script is safe to run repeatedly:
- it does not create tasks
- it does not modify the SQLite database
- it does not delete data
- it refuses to overwrite a different existing config file

Configuration is read from .env and versions.env in the repository when those
files exist. Environment variables take precedence.
EOF
}

load_local_values() {
    file=$1
    [ -f "$file" ] || return 0

    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            ''|\#*) continue ;;
        esac
        case "$line" in
            export\ *) line=${line#export } ;;
        esac

        key=${line%%=*}
        value=${line#*=}
        case "$key" in
            TASKLITE_CONFIG_FILE)
                [ "${TASKLITE_CONFIG_FILE+x}" = x ] || TASKLITE_CONFIG_FILE=$value
                ;;
            TASKLITE_ATTACHMENTS_PUBLIC_BASE)
                [ -n "$ATTACHMENTS_WEB_URL" ] || ATTACHMENTS_WEB_URL=$value
                ;;
        esac
    done < "$file"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf '%s\n' "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

load_local_values "$ROOT_DIR/.env"
load_local_values "$ROOT_DIR/versions.env"

CONFIG_FILE=${CONFIG_FILE:-${TASKLITE_CONFIG_FILE:-"$HOME/.config/tasklite/config.yaml"}}

case "$ATTACHMENTS_WEB_URL" in
    ''|*[!A-Za-z0-9:/._?=-]*)
        printf '%s\n' 'Missing or invalid TASKLITE_ATTACHMENTS_PUBLIC_BASE.' >&2
        printf '%s\n' 'Set it in versions.env or export it before running this script.' >&2
        exit 1
        ;;
esac

CONFIG_DIR=$(dirname -- "$CONFIG_FILE")
TMP_FILE=$(mktemp)
trap 'rm -f "$TMP_FILE"' EXIT HUP INT TERM

cat > "$TMP_FILE" <<EOF
attachmentsWebUrl: $ATTACHMENTS_WEB_URL

shortcuts:
  homelab:
    tag: homelab
  hermes:
    tag: hermes
  arbeit:
    tag: arbeit
  kaufen:
    tag: kaufen
EOF

if [ -f "$CONFIG_FILE" ]; then
    if cmp -s "$TMP_FILE" "$CONFIG_FILE"; then
        printf '%s\n' "Personal Task-Stack config already matches: $CONFIG_FILE"
        exit 0
    fi

    printf '%s\n' "Refusing to overwrite existing config: $CONFIG_FILE" >&2
    printf '%s\n' 'Review the existing file and apply changes manually if desired.' >&2
    exit 1
fi

if [ "$DRY_RUN" = true ]; then
    printf '%s\n' "Would create: $CONFIG_FILE"
    cat "$TMP_FILE"
    exit 0
fi

mkdir -p "$CONFIG_DIR"
cp "$TMP_FILE" "$CONFIG_FILE"
printf '%s\n' "Created personal Task-Stack config: $CONFIG_FILE"
printf '%s\n' 'No tasks, attachments, or database records were changed.'
