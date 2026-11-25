#!/bin/bash
# Installer for Notepad (Windows 11 style) on Raspberry Pi
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" = "0" ]; then
  echo "Run this as your normal user (not with sudo). It will ask for sudo when needed."
  exit 1
fi

echo "==> Installing packages"
sudo apt-get update
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gtksource-4 xdg-utils
sudo apt-get install -y fonts-open-sans || echo "   (Open Sans font not available, using system font)"
for p in ; do
  sudo apt-get install -y "$p" || echo "   ($p not available, skipping)"
done

echo "==> Installing app"
sudo install -d /opt/pi-notepad
sudo install -m 644 "$SRC/pi_notepad.py" /opt/pi-notepad/pi_notepad.py
printf '#!/bin/sh\nexec /usr/bin/python3 /opt/pi-notepad/pi_notepad.py "$@"\n' | sudo tee /usr/local/bin/pi-notepad >/dev/null
sudo chmod 755 /usr/local/bin/pi-notepad

echo "==> Adding menu entry and icon"
sudo install -D -m 644 "$SRC/pi-notepad.svg" /usr/share/icons/hicolor/scalable/apps/pi-notepad.svg
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
sudo tee /usr/share/applications/pi-notepad.desktop >/dev/null <<'DESK'
[Desktop Entry]
Type=Application
Name=Notepad
GenericName=Text Editor
Comment=Edit text files
Exec=pi-notepad %F
Icon=pi-notepad
Terminal=false
Categories=Utility;TextEditor;GTK;
MimeType=text/plain;
StartupWMClass=pi-notepad
StartupNotify=true
DESK
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true

echo "==> Making Notepad the default app for its file types"
mkdir -p "$HOME/.config/pi-notepad"
for t in text/plain; do
  old=$(xdg-mime query default "$t" 2>/dev/null || true)
  if [ -n "$old" ] && [ "$old" != "pi-notepad.desktop" ]; then
    echo "$t $old" >> "$HOME/.config/pi-notepad/old-defaults"
  fi
  xdg-mime default pi-notepad.desktop "$t" 2>/dev/null || true
done

echo
echo "Done. Open Notepad from the menu or run: pi-notepad"
