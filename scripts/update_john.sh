#!/bin/bash
# Install or update John the Ripper (jumbo). Clones on first run, pulls thereafter.
set -e
JOHN_PATH="/opt/cracking-tools/john"
echo "Installing/updating John the Ripper..."
sudo git config --global --add safe.directory "$JOHN_PATH" 2>/dev/null || true
if [ -d "$JOHN_PATH/.git" ]; then
    sudo git -C "$JOHN_PATH" pull origin bleeding-jumbo
else
    sudo mkdir -p "$(dirname "$JOHN_PATH")"
    sudo git clone --depth 1 -b bleeding-jumbo https://github.com/openwall/john "$JOHN_PATH"
fi
cd "$JOHN_PATH/src"
sudo ./configure
sudo make -s clean
sudo make -sj"$(nproc)"
echo "John the Ripper ready at $JOHN_PATH/run/john"
