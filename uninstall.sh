#!/bin/bash
# Removes Notepad.
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" = "0" ]; then
  echo "Run this as your normal user (not with sudo)."
  exit 1
fi

# put back the apps that opened these file types before
if [ -f "$HOME/.config/pi-notepad/old-defaults" ]; then
  while read -r t old; do
    [ -n "$old" ] && xdg-mime default "$old" "$t" 2>/dev/null || true
  done < "$HOME/.config/pi-notepad/old-defaults"
  rm -f "$HOME/.config/pi-notepad/old-defaults"
fi

sudo rm -rf /opt/pi-notepad /usr/local/bin/pi-notepad /usr/share/applications/pi-notepad.desktop \
  /usr/share/icons/hicolor/scalable/apps/pi-notepad.svg
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true
echo "Notepad removed. Your settings are still in ~/.config/pi-notepad (delete that folder to remove them)."
