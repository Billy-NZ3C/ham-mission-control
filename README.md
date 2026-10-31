# Ham Mission Control

A full-screen ham radio clock for your shack TV or monitor. A live 3D Earth, a radar scope
centered on your QTH, and every station that hears you lighting up the globe in real time.

![Ham Mission Control](screenshot.png)

**What's on the screen**

- **3D Earth** with real day/night, city lights and clouds, turning slowly
- **Live signals from PSKReporter.** Worldwide FT8 and CW traffic draws colored arcs (color = band).
  When someone decodes *you*, a bright beam fires from your QTH to them and the camera swings over.
- **"On the air" panel.** How many stations heard you in the last 30 minutes, the farthest, the loudest,
  and the last five
- **Radar scope** centered on your QTH with true beam headings, showing stations hearing you,
  DX cluster spots, satellites and your logbook contacts
- **Amateur satellites** in orbit at their real height, plus the next 3 passes over you
- **UTC and local clocks**, local weather (plus US weather alerts), and space weather (SFI, Kp, A index, X-ray)
- **DX cluster** ticker along the bottom
- **Your logbook contacts** on the globe: drag an ADIF file onto the screen

No accounts, no API keys, nothing to install for the basic clock. It's one web page.

---

## Quick start (about 2 minutes)

1. **Download** this project: green **Code** button → **Download ZIP**, then unzip it.
2. **Double-click `index.html`** to open it in **Google Chrome** (recommended) or another modern browser.
   If the computer asks which program to open it with, pick Chrome (or Edge/Safari).
3. **Fill in the setup screen** that appears the first time: your call sign, your **grid square**
   (it fills in latitude and longitude for you), your town and your time zone, then click **Save & Start**.
   - Want an exact spot instead of the middle of your grid? Right-click your house in Google Maps and click
     the numbers at the top of the menu to copy them. The first number is latitude, the second is longitude.
   - Leave **Relay address** blank unless you set up the relay (below).
   - To change anything later, click **⚙ SETUP** beside the globe or press **S**.
4. Press **F11** (Windows/Linux) or **Ctrl+Cmd+F** (Mac) for full screen.

Your settings are saved in that browser. If you'd rather build them into the file itself (for example on a
kiosk that gets wiped), open `index.html` in a text editor and change the `YOUR SETTINGS` lines near the top
of the script. Settings saved from the setup screen win over those lines.

It needs an internet connection. The "stations hearing you" panel starts counting from when the page
opens, so get on the air with FT8 or CW and watch the beams come in.

**Your logbook contacts:** export an ADIF (`.adi`) file from your logging program, QRZ, or LoTW and
**drag it onto the clock**. The browser remembers it next time. Until then it shows sample contacts.

**Moving the globe:** drag it with the mouse to turn it. It holds there for a minute, then starts turning
slowly again. Press **Space** (or click **⏸ STOP GLOBE** beside it) to stop the turning altogether, and again
to restart it. While you're holding the view, the camera doesn't swing to stations that hear you.

**Keyboard:** **S** opens setup, **Space** stops/starts the globe, **T** previews every pop-up, and **R**
shows a pretend rig on the air.

---

## Optional: the relay (live rig display + new contacts)

A web page can't listen to your radio software or read your QRZ logbook by itself. The small relay
program does that and passes it to the clock. With it you get:

- A **RIG card** with your frequency and mode, and a red **ON AIR** light when you transmit
- A pop-up and a beam on the globe every time you **log a contact**
- New contacts and **new confirmations** from your **QRZ logbook**, with fireworks for a new confirmed country

It works with **WSJT-X**, and with programs that speak WSJT-X's network protocol, such as **JTDX**, **MSHV**
and **Nexus**.

**Which computer runs it?** One that's on whenever you want the clock: your radio computer, a Raspberry Pi,
a mini PC, or the computer driving your TV. Windows, Mac or Linux all work.

### Step 1: Put the files on that computer

Download the ZIP (green **Code** button → **Download ZIP**) and unzip it into a folder called `hamclock`,
for example `C:\hamclock` on Windows or `hamclock` in your home folder on Linux/Mac. Keep the files together:
the relay serves the `index.html` from that folder, so there's nothing to copy around.

### Step 2: Start the relay

**Windows**
1. Install **Python** from [python.org/downloads](https://www.python.org/downloads/). On the first installer
   screen, **tick "Add python.exe to PATH"**, then click **Install Now**.
2. Open the `hamclock` folder, then the `relay` folder, and **double-click `start-relay-windows.bat`**.
3. If **Windows Firewall** asks about Python, tick **Private networks** and click **Allow access**.
4. A black window opens and shows a line like `OPEN THE CLOCK AT: http://192.168.1.50:8088/`.
   **Write that address down.** Leave the window open (you can minimise it).
5. To start it automatically: press **Windows key + R**, type `shell:startup`, press Enter, and drag a
   **shortcut** of `start-relay-windows.bat` into that folder (right-click drag → **Create shortcuts here**).

**Raspberry Pi / Linux** (Python is already installed)

```bash
cd ~/hamclock/relay
python3 clock_relay.py
```

**Mac:** open Terminal, type `cd ` (with a space), drag the `relay` folder into the window, press Enter,
then type `python3 clock_relay.py`. If the Mac offers to install developer tools for Python, click **Install**.

Either way it prints `OPEN THE CLOCK AT: http://...` with the address to use. To start it automatically on
Linux, see below.

### Step 3: Open the clock from the relay

On the computer driving your TV, open the address the relay printed (for example `http://192.168.1.50:8088/`)
in Chrome. On the relay computer itself, `http://localhost:8088/` works too. The setup screen appears once.

*Or*, if you'd rather keep opening `index.html` as a file, put the relay's address in the **Relay address**
box on the setup screen (**⚙ SETUP** or **S**).

### Step 4: Point your FT8 program at the relay

Use the address the relay printed, **without** `http://` and `:8088`, for example `192.168.1.50`.
If the FT8 program runs on the **same** computer as the relay, use `127.0.0.1`.

- **WSJT-X / JTDX:** **File → Settings → Reporting → UDP Server** = that address, port **2237**.
  If you also use JTAlert or GridTracker, use the multicast address `224.0.0.1` instead.
- **Nexus:** **Settings → Logging & Connectors → Integrations & Feeds** → turn on **WSJT-X UDP API** and set
  **UDP Address** to that address with `:2237`, for example `192.168.1.50:2237`. Your QRZ / Club Log
  uploads in Nexus are not affected.

The RIG card shows your frequency within about 15 seconds of decoding.

**Test it:** open `http://192.168.1.50:8088/test?type=qso` (your relay's address) and a fake pop-up appears
on the clock. `.../test?type=confirm` shows a confirmation.

### Step 5 (optional): QRZ logbook

1. In the `relay` folder, make a copy of `relay.example.ini` and name the copy `relay.ini`.
   (Windows hides the `.ini` part, so the files show as `relay.example` and `relay`.)
2. Open `relay.ini` in Notepad/TextEdit and paste your QRZ Logbook API key after `api_key =`
   (QRZ.com → My Logbook → Settings). QRZ may require a subscription for API downloads.
3. Close the relay window and start it again.

The first time, it quietly learns your whole log and only announces things that are new after that.
`relay.ini` stays on your computer: it's in `.gitignore`, so it never gets uploaded.

### Start the relay automatically (Linux / Raspberry Pi)

```bash
mkdir -p ~/.config/systemd/user
cp ~/hamclock/relay/hamclock-relay.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hamclock-relay
sudo loginctl enable-linger $USER
```

The service file expects the project at `~/hamclock`. If you put it somewhere else, edit the two paths
in `hamclock-relay.service`. Check on it with `systemctl --user status hamclock-relay`.

### Turn a Raspberry Pi or mini PC into a dedicated display

1. Set the computer to **log in automatically** (Ubuntu: Settings → Users → Automatic Login), so the clock comes
   back by itself after a power cut.
2. Install Google Chrome (or Chromium; change `google-chrome` to `chromium` in the script).
3. Make the clock open full screen at login:

   ```bash
   chmod +x ~/hamclock/kiosk/clock-kiosk.sh
   mkdir -p ~/.config/autostart
   cp ~/hamclock/kiosk/hamclock-kiosk.desktop ~/.config/autostart/
   ```

   The script waits for the relay to start and stops Chrome showing a "restore pages?" bar after a power cut.
   If the relay runs on a different computer, change `URL=` at the top of `kiosk/clock-kiosk.sh`.
4. Stop the screen from blanking (Ubuntu): Settings → Power → **Screen Blank: Never**, and turn off
   **Automatic Suspend**.

To get out of full screen, press **Alt+F4**.

### If the RIG card stays on "waiting"

- **Check the radio computer can reach the relay.** On Windows, open PowerShell and run
  `Test-NetConnection 192.168.1.50 -Port 8088` (your relay's address). It should say `TcpTestSucceeded : True`.
- **VPNs can block it.** **Tailscale**, or a VPN that comes with antivirus software, can send your home network
  traffic into the VPN instead. If the test above fails and shows a VPN in `InterfaceAlias`, turn off
  **"Use Tailscale subnets"** / set **Exit node: None**, or turn on **"Allow local network access"** in your VPN.
- **Restart your FT8 program** after changing its UDP setting.
- Test the relay itself from any browser: `http://<relay address>:8088/events?after=-1` shows what it has received.

---

## Put the clock on your website

The clock has a **website mode** for showing it inside a page (an iframe). It's locked to the call and
location in the link: no setup screen, buttons, keyboard shortcuts or relay, and a lighter worldwide feed.
Visitors can still drag the globe.

```
https://billy-nz3c.github.io/ham-mission-control/?embed=1&call=N0CALL&grid=EM28&town=LEBANON%20KS&tz=America/Chicago
```

Change `call`, `grid` (or use `lat=` and `lon=` instead), `town` (spaces become `%20`) and `tz`.
On your page:

```html
<div style="aspect-ratio:16/9"><iframe src="(the link above)" style="width:100%;height:100%;border:0" allow="fullscreen"></iframe></div>
```

The 3D globe is heavy for phones, so on small screens it's kinder to show `poster.jpg` with a link that opens
the clock full screen.

## Notes

- **Weather alerts** come from the US National Weather Service, so they only appear in the US.
  Temperature is in °F and distances are in miles.
- **The "who hears you" data** comes from PSKReporter, so it works for digital modes and CW reported
  there (FT8, FT4, CW and so on). Phone (SSB) contacts don't show there; use the relay for those.
- **The screen is designed for 1920x1080** and scales to fit any screen size.
- **Privacy:** your settings stay on your computer. `relay.ini` (with your QRZ key) is in `.gitignore`,
  so it won't be uploaded if you fork this project.

## Data sources and credits

Thank you to the free services that make this work:
[PSKReporter](https://pskreporter.info) (live reception reports),
[CelesTrak](https://celestrak.org) (satellite orbits),
[NOAA SWPC](https://www.swpc.noaa.gov) (space weather),
[Open-Meteo](https://open-meteo.com) (weather),
[US National Weather Service](https://www.weather.gov) (alerts),
[HamQTH](https://www.hamqth.com) (DX cluster),
[callook.info](https://callook.info) (US call sign locations),
NASA Blue Marble imagery (Earth textures), and the open-source libraries
[three.js](https://threejs.org), [satellite.js](https://github.com/shashwatak/satellite-js),
[D3](https://d3js.org) and [MQTT.js](https://github.com/mqttjs/MQTT.js).

Please be kind to these services. The clock already caches and spaces out its requests, so don't
shorten its timers.

## License

MIT. Free to use, change and share. See [LICENSE](LICENSE). 73!
