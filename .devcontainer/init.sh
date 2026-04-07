#!/usr/bin/env bash
# Wird auf dem HOST vor dem Container-Start ausgeführt (initializeCommand).
# Docker bind-mounts verlangen, dass die Quellpfade existieren – z. B. fehlt
# /mnt/wslg/PulseServer ohne WSLg oder auf nativem Linux.

set -u

echo "[.devcontainer/init.sh] Host-Vorbereitung für optionale Bind-Mounts..."

# X11-Socket-Verzeichnis (oft schon vorhanden)
if [ ! -d /tmp/.X11-unix ]; then
  if mkdir -p /tmp/.X11-unix 2>/dev/null; then
    :
  elif command -v sudo >/dev/null 2>&1; then
    sudo mkdir -p /tmp/.X11-unix || true
  else
    echo "[.devcontainer/init.sh] Hinweis: /tmp/.X11-unix fehlt – GUI vom Host aus ggf. nicht nutzbar."
  fi
fi

# WSLg PulseAudio-Socket (oder Platzhalter, damit docker run nicht abbricht)
if [ ! -e /mnt/wslg/PulseServer ]; then
  if command -v sudo >/dev/null 2>&1; then
    sudo mkdir -p /mnt/wslg
    sudo touch /mnt/wslg/PulseServer 2>/dev/null || true
    echo "[.devcontainer/init.sh] Platzhalter /mnt/wslg/PulseServer angelegt (kein echtes WSLg-Audio ohne Windows/WSLg)."
  else
    echo "[.devcontainer/init.sh] WARNUNG: /mnt/wslg/PulseServer fehlt und kein sudo – Container-Start kann am Bind-Mount scheitern."
  fi
fi

echo "[.devcontainer/init.sh] Fertig."
