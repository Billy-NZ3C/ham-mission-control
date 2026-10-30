# Updating your clock

Updating means swapping one file, `index.html`. Nothing to install, and the relay program doesn't need
to change unless the update notes say so.

## Steps

1. **Get the new `index.html`** (from the email, or from GitHub: green **Code** button → **Download ZIP**,
   then unzip it).
2. **Check the name.** It must be exactly `index.html`. Some email programs rename attachments to
   something like `index (1).html`; if so, rename it.
3. **Replace the old one.** Go to the folder your clock is in, delete the old `index.html` (or let the new
   one replace it), and put the new `index.html` there.
4. **If you run the relay**, also update it, so you never have to copy `index.html` around again:
   - Replace `relay/clock_relay.py` with the new one (keep your `relay.ini`).
   - **Delete** the `www` folder inside `relay` (it held the old copy of the clock). The new relay shows the
     `index.html` from the main folder instead.
   - Restart the relay (`systemctl --user restart hamclock-relay`, or close it and start it again).
   - New too: the RIG card names the program sending it (Nexus, JTDX, ...), and Windows users get a
     double-click `start-relay-windows.bat`.
5. **Open the clock the same way you always do**, and press **Ctrl+Shift+R** (Mac: **Cmd+Shift+R**) so the
   browser loads the new version instead of a saved copy.

## The first time after this update: the setup screen

Older versions had your call sign and location typed into the file. This version asks for them on screen
instead, so a **Station Setup** screen appears once:

- **Call sign**
- **Grid square**: type it and latitude/longitude fill in by themselves (or type exact lat/lon)
- **Town**: shown under your call sign
- **Time zone**: pick from the list (it starts on your computer's time zone)
- **Relay address**: leave blank if you don't run the relay. If you open the clock as a file and do run
  the relay, enter its address, for example `http://192.168.1.50:8088`.

Click **Save & Start**. The browser remembers these, so future updates won't ask again.

**New call sign or moved?** Click **⚙ SETUP** beside the globe, or press **S**, change what you need, and
click **Save & Start**. **Esc** or **Cancel** closes it without changes.

## Good to know

- **Each browser keeps its own settings.** If you open the clock in more than one place (a laptop file and
  the TV via the relay, or Chrome and Firefox), fill in setup once in each.
- **Your logbook contacts** (the ADIF file you dragged on) are kept, as long as you open the clock the same
  way, in the same browser, as before.
- **New in this version:**
  - The globe no longer spins wildly for a few seconds when a station hears you.
  - Drag the globe with the mouse to turn it. It stays for a minute, then resumes its slow turn.
  - **Space** (or the **⏸ STOP GLOBE** button) stops the globe turning; press again to restart.
  - **S** opens setup.
