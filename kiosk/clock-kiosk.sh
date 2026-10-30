#!/bin/bash
# Opens the clock full screen (Linux kiosk). Started at login by ~/.config/autostart/hamclock-kiosk.desktop.
# Change URL if the relay runs on a different computer.
# Waits for the relay (it starts at the same moment), and tells Chrome its last exit was clean so it never shows
# a "restore pages?" bar across the clock after a power cut.
URL=http://localhost:8088/
for i in $(seq 1 60); do curl -fs -o /dev/null "$URL" && break; sleep 1; done
PREFS=~/.config/google-chrome/Default/Preferences
[ -f "$PREFS" ] && sed -i 's/"exit_type":"[^"]*"/"exit_type":"Normal"/; s/"exited_cleanly":false/"exited_cleanly":true/' "$PREFS"
exec google-chrome --kiosk --noerrdialogs --disable-infobars --no-first-run --password-store=basic \
  --disable-session-crashed-bubble --disable-features=Translate "$URL"
