#!/bin/bash
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo -e 'Script must be run as root. Use sudo, su, or add "USER root" to your Dockerfile before running this script.'
    exit 1
fi

echo "========================================="
echo "Installing devtools..."
echo "========================================="

# Yarn-Repo entfernen BEVOR apt-get update (bekanntes Problem im Basis-Image)
echo "Removing broken Yarn repository..."
rm -f /etc/apt/sources.list.d/yarn.list

echo "Updating package lists..."
apt-get update

echo "Installing packages..."
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    portaudio19-dev \
    libsndfile1 \
    tk \
    liblapack-dev \
    libblas-dev \
    libatlas-base-dev \
    gfortran \
    pulseaudio-utils

echo "Upgrading pip (uv wird über Dev-Container-Feature installiert)..."
python -m pip install --upgrade pip

echo "Unlocking vscode login (kein festes Passwort im Image)..."
passwd -d vscode 2>/dev/null || true

rm -rf /var/lib/apt/lists/*

echo "========================================="
echo "devtools installation completed!"
echo "========================================="
