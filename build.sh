#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo "Syncing dependencies (stats + dev)..."
uv sync --extra stats --extra dev

echo "Building onedir executable..."
uv run pyinstaller \
    --noconsole \
    --onedir \
    --name wotiti \
    --icon "src/assets/wotiti.ico" \
    --hidden-import=tkinter.filedialog \
    --collect-submodules sklearn \
    --collect-submodules scipy \
    --exclude-module torch \
    --add-data "src/assets:assets" \
    src/main.py

DIST_DIR="$REPO_ROOT/dist/wotiti"

if [ ! -d "$DIST_DIR" ]; then
    echo "ERROR: Build output not found: $DIST_DIR" >&2
    exit 1
fi

echo "Placing data/ next to executable..."
DATA_DST="$DIST_DIR/data"
if [ -d "$DATA_DST" ]; then
    rm -rf "$DATA_DST"
fi
cp -r "$REPO_ROOT/data" "$DATA_DST"
mkdir -p "$DATA_DST/sounds"
# Do not ship developer-local config with absolute paths.
rm -f "$DATA_DST/config.json"
# Ship an empty runtime database (app creates schema on first start).
rm -f "$DATA_DST/app_database.db"
: > "$DATA_DST/app_database.db"

# Create helper scripts for per-user autostart on Linux desktop environments.
TOOLS_DIR="$DIST_DIR/tools"
mkdir -p "$TOOLS_DIR"

cat > "$TOOLS_DIR/enable_autostart.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_BIN="$DIST_DIR/wotiti"

if [[ ! -x "$APP_BIN" ]]; then
    echo "ERROR: Executable not found or not executable: $APP_BIN" >&2
    exit 1
fi

AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/wotiti.desktop"

mkdir -p "$AUTOSTART_DIR"

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=WoTiTi
Comment=Work Time Tracker
Exec=$APP_BIN
Path=$DIST_DIR
Terminal=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
DESKTOP

ICON_FILE="$DIST_DIR/assets/wotiti.ico"
if [[ -f "$ICON_FILE" ]]; then
    printf 'Icon=%s\n' "$ICON_FILE" >> "$DESKTOP_FILE"
fi

chmod 644 "$DESKTOP_FILE"
echo "Autostart aktiviert: $DESKTOP_FILE"
EOF

cat > "$TOOLS_DIR/disable_autostart.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/wotiti.desktop"

if [[ -f "$DESKTOP_FILE" ]]; then
    rm -f "$DESKTOP_FILE"
    echo "Autostart deaktiviert: $DESKTOP_FILE"
else
    echo "Kein Autostart-Eintrag gefunden: $DESKTOP_FILE"
fi
EOF

chmod +x "$TOOLS_DIR/enable_autostart.sh" "$TOOLS_DIR/disable_autostart.sh"

echo "Build complete: $DIST_DIR/wotiti"
