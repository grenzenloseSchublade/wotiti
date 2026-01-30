#!/bin/bash
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo -e 'Script must be run as root. Use sudo, su, or add "USER root" to your Dockerfile before running this script.'
    exit 1
fi

echo "========================================="
echo "Installing devtools..."
echo "========================================="

# WICHTIG: Yarn-Repo entfernen BEVOR apt-get update
echo "Removing broken Yarn repository..."
rm -f /etc/apt/sources.list.d/yarn.list

# Jetzt apt-get update
echo "Updating package lists..."
apt-get update

packages="portaudio19-dev
          libsndfile1
          tk
          liblapack-dev
          libblas-dev
          libatlas-base-dev 
          gfortran"

echo "Installing packages..."
for package in $packages; do
    echo "Installing $package..."
    apt-get install -y $package
done

echo "Upgrading packages..."
apt-get upgrade -y

echo "Upgrading pip and installing uv..."
python -m pip install --upgrade pip
python -m pip install --no-cache-dir uv

echo "Setting up vscode user password..."
passwd -d vscode 2>/dev/null || true
echo "vscode:qwertz." | chpasswd

echo "========================================="
echo "devtools installation completed!"
echo "========================================="
