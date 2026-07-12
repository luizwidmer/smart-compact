#!/bin/sh
set -eu

repo_slug=${SMART_COMPACT_REPO:-luizwidmer/smart-compact}
ref=${SMART_COMPACT_REF:-main}

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || true)
if [ -n "$script_dir" ] && [ -f "$script_dir/scripts/install_smart_compact.py" ]; then
    exec python3 "$script_dir/scripts/install_smart_compact.py" "$@"
fi

command -v python3 >/dev/null 2>&1 || {
    echo "Smart Compact requires python3." >&2
    exit 1
}
command -v curl >/dev/null 2>&1 || {
    echo "Smart Compact bootstrap requires curl." >&2
    exit 1
}
command -v tar >/dev/null 2>&1 || {
    echo "Smart Compact bootstrap requires tar." >&2
    exit 1
}

temporary=$(mktemp -d "${TMPDIR:-/tmp}/smart-compact.XXXXXX")
trap 'rm -rf "$temporary"' EXIT HUP INT TERM

curl -fsSL "https://codeload.github.com/$repo_slug/tar.gz/$ref" | tar -xz -C "$temporary"

source_dir=
for candidate in "$temporary"/*; do
    if [ -f "$candidate/scripts/install_smart_compact.py" ]; then
        source_dir=$candidate
        break
    fi
done

if [ -z "$source_dir" ]; then
    echo "Downloaded archive does not contain the Smart Compact installer." >&2
    exit 1
fi

python3 "$source_dir/scripts/install_smart_compact.py" "$@"
