#!/usr/bin/env python3
"""Ham Mission Control relay: runs on an always-on computer (Raspberry Pi, mini PC, Linux box) and feeds the clock.

The clock (a web page) can't listen to your radio software or read QRZ itself, so this little
server does it and hands the clock a list of things to show:

  * logged contacts     - WSJT-X "QSO logged" messages, and new contacts in your QRZ logbook
  * QRZ confirmations   - a QRZ logbook contact that turns confirmed (QRZ, LoTW or card)
  * rig display         - WSJT-X status: dial frequency, mode, and whether it's transmitting

The clock asks  GET /events?after=<last id>  every few seconds.  It also serves the clock page
itself at  http://<this PC>:8088/  so a Pi or TV browser can just open that address.
Try a fake one:  http://<this PC>:8088/test?type=qso   (qso, confirm)

Standard library only. Settings in relay.ini next to this file.
"""

import configparser
import html
import json
import logging
import os
import re
import socket
import struct
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
log = logging.getLogger("clock-relay")

cfg = configparser.ConfigParser()
cfg.read(os.path.join(HERE, "relay.ini"))
PORT = cfg.getint("relay", "port", fallback=8088)
WWW = os.path.join(HERE, "www")                                   # optional: put a custom index.html here
CLOCK_PAGE = os.path.join(os.path.dirname(HERE), "index.html")      # otherwise the one in the main folder
QRZ_KEY = cfg.get("qrz", "api_key", fallback="").strip()
QRZ_EVERY = cfg.getint("qrz", "check_every_seconds", fallback=180)
WSJTX_PORT = cfg.getint("wsjtx", "udp_port", fallback=2237)
WSJTX_GROUP = cfg.get("wsjtx", "multicast_group", fallback="224.0.0.1").strip()
UA = "ham-mission-control-relay/1.0"

# ---------------------------------------------------------------- shared state
lock = threading.Lock()
events = []          # newest last, each has a unique increasing "id"
next_id = 1
rig = {}             # latest WSJT-X status
recent_qsos = {}     # "CALL|band" -> time, so WSJT-X and QRZ don't announce the same contact twice


def add_event(ev):
    global next_id
    with lock:
        ev = {"id": next_id, "t": ev.get("t") or int(time.time()), **ev}
        next_id += 1
        events.append(ev)
        del events[:-200]
    log.info("event %s", json.dumps(ev))


def band_of(mhz):
    for lo, hi, b in [(1.8, 2, "160m"), (3.5, 4, "80m"), (5.3, 5.41, "60m"), (7, 7.3, "40m"), (10.1, 10.15, "30m"),
                      (14, 14.35, "20m"), (18.068, 18.168, "17m"), (21, 21.45, "15m"), (24.89, 24.99, "12m"),
                      (28, 29.7, "10m"), (50, 54, "6m"), (144, 148, "2m"), (420, 450, "70cm")]:
        if lo <= mhz <= hi:
            return b
    return ""


def grid_to_latlon(g):
    g = (g or "").strip().upper()
    if not re.match(r"^[A-R]{2}[0-9]{2}", g):
        return None
    lon = (ord(g[0]) - 65) * 20 - 180 + int(g[2]) * 2
    lat = (ord(g[1]) - 65) * 10 - 90 + int(g[3])
    if re.match(r"^[A-R]{2}[0-9]{2}[A-X]{2}", g):
        lon += (ord(g[4]) - 65) / 12 + 1 / 24
        lat += (ord(g[5]) - 65) / 24 + 1 / 48
    else:
        lon += 1
        lat += .5
    return round(lat, 3), round(lon, 3)


def callook(call):
    """US call -> name, town, lat/lon from the FCC database (callook.info). None if not found."""
    try:
        req = urllib.request.Request(f"https://callook.info/{urllib.parse.quote(call)}/json", headers={"User-Agent": UA})
        d = json.loads(urllib.request.urlopen(req, timeout=15).read())
        if d.get("status") != "VALID":
            return None
        loc = d.get("location") or {}
        return {"lat": float(loc["latitude"]), "lon": float(loc["longitude"]), "grid": loc.get("gridsquare", ""),
                "town": re.sub(r"\s+\d{5}(-\d{4})?$", "", (d.get("address") or {}).get("line2", "")).title()}
    except Exception as e:
        log.info("callook %s: %s", call, e)
        return None


def new_qso(call, band, mode, src, grid="", lat=None, lon=None, country="", state=""):
    """Announce a logged contact once, whichever source (WSJT-X or QRZ) sees it first."""
    key = f"{call.upper()}|{band}"
    now = time.time()
    with lock:
        for k, t in list(recent_qsos.items()):
            if now - t > 3 * 3600:
                del recent_qsos[k]
        if key in recent_qsos:
            return
        recent_qsos[key] = now
    if lat is None and grid:
        ll = grid_to_latlon(grid)
        if ll:
            lat, lon = ll
    if lat is None:
        c = callook(call)
        if c:
            lat, lon, grid = c["lat"], c["lon"], grid or c["grid"]
            state = state or c["town"]
    add_event({"type": "qso", "call": call.upper(), "band": band, "mode": mode, "src": src, "grid": grid[:6],
               "lat": lat, "lon": lon, "where": country or state})


# ---------------------------------------------------------------- WSJT-X UDP (status + QSO logged)
class QReader:
    """Reads Qt QDataStream fields, the format WSJT-X uses for its UDP messages."""
    def __init__(self, b):
        self.b, self.i = b, 0

    def _u(self, fmt):
        v = struct.unpack_from(">" + fmt, self.b, self.i)[0]
        self.i += struct.calcsize(">" + fmt)
        return v

    def u8(self): return self._u("B")
    def u32(self): return self._u("I")
    def u64(self): return self._u("Q")
    def i64(self): return self._u("q")
    def boolean(self): return self.u8() != 0

    def utf8(self):
        n = self.u32()
        if n == 0xFFFFFFFF:
            return ""
        s = self.b[self.i:self.i + n].decode("utf-8", "replace")
        self.i += n
        return s

    def datetime(self):
        self.i64(); self.u32()        # julian day, ms since midnight
        if self.u8() == 2:            # timespec 2 carries an offset
            self._u("i")


APP_NAMES = {"Tempo": "Nexus"}   # ids some programs send that aren't their display name


def listen_wsjtx():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", WSJTX_PORT))
    if WSJTX_GROUP:
        try:   # also hear WSJT-X when it's set to the multicast address (lets JTAlert/GridTracker share the feed)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(WSJTX_GROUP) + socket.inet_aton("0.0.0.0"))
        except OSError as e:
            log.info("multicast %s not joined: %s", WSJTX_GROUP, e)
    log.info("listening for WSJT-X on UDP %s", WSJTX_PORT)
    while True:
        data, addr = s.recvfrom(65535)
        try:
            r = QReader(data)
            if r.u32() != 0xADBCCBDA:
                continue
            r.u32()                      # schema
            kind = r.u32()
            app = r.utf8() or "WSJT-X"   # sender's id, shown on the RIG card: "WSJT-X", "JTDX", ...
            app = APP_NAMES.get(app, app)
            if kind == 1:                # Status
                dial = r.u64(); mode = r.utf8(); dx = r.utf8(); r.utf8(); r.utf8()
                r.boolean(); tx = r.boolean()
                with lock:
                    rig.update(src=app, freq=dial, mode=mode, band=band_of(dial / 1e6), tx=tx, dx=dx, t=time.time())
            elif kind == 6:              # Close
                with lock:
                    rig.clear()
            elif kind == 5:              # QSO logged
                r.datetime(); call = r.utf8(); grid = r.utf8(); freq = r.u64(); mode = r.utf8()
                threading.Thread(target=new_qso, args=(call, band_of(freq / 1e6), mode, app, grid), daemon=True).start()
        except Exception as e:
            log.info("WSJT-X message from %s not understood: %s", addr[0], e)


# ---------------------------------------------------------------- QRZ logbook (new contacts + confirmations)
QRZ_STATE = os.path.join(HERE, "qrz-state.json")


def qrz_call(option):
    body = urllib.parse.urlencode({"KEY": QRZ_KEY, "ACTION": "FETCH", "OPTION": option}).encode()
    req = urllib.request.Request("https://logbook.qrz.com/api", data=body, headers={"User-Agent": UA})
    text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    result = (re.search(r"RESULT=(\w+)", text) or [None, ""])[1]
    if result != "OK":
        reason = (re.search(r"REASON=([^&]*)", text) or [None, text[:200]])[1]
        raise RuntimeError(f"QRZ said {result}: {urllib.parse.unquote_plus(reason)}")
    m = re.search(r"ADIF=(.*)", text, re.S)
    adif = m.group(1) if m else ""
    if "%3C" in adif[:200].upper():
        adif = urllib.parse.unquote_plus(adif)
    return parse_adif(html.unescape(adif))


def parse_adif(text):
    out = []
    for rec in re.split(r"(?i)<eor>", text):
        f, i = {}, 0
        for m in re.finditer(r"<(\w+):(\d+)(?::\w)?>", rec):
            n = int(m.group(2))
            f[m.group(1).lower()] = rec[m.end():m.end() + n]
        if f.get("call"):
            out.append(f)
    return out


def confirmed(f):
    return f.get("app_qrzlog_status", "").upper() == "C" or f.get("lotw_qsl_rcvd", "").upper() == "Y" \
        or f.get("qsl_rcvd", "").upper() == "Y"


def poll_qrz():
    if not QRZ_KEY:
        log.info("no QRZ API key in relay.ini; QRZ contacts/confirmations are off")
        return
    try:
        state = json.load(open(QRZ_STATE))
    except Exception:
        state = {}
    seen = state.get("seen", {})            # logid -> confirmed?
    if not seen:                             # first run: learn the whole log quietly, announce nothing
        after = 0
        for _ in range(60):
            recs = qrz_call(f"MAX:250,AFTERLOGID:{after}")
            for f in recs:
                seen[f.get("app_qrzlog_logid", "")] = confirmed(f)
            ids = [int(f["app_qrzlog_logid"]) for f in recs if f.get("app_qrzlog_logid", "").isdigit()]
            if len(recs) < 250 or not ids:
                break
            after = max(ids)
        state["countries"] = []
        log.info("QRZ: learned %d contacts", len(seen))
    countries = set(state.get("countries", []))
    while True:
        try:
            since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
            announced = 0
            for f in qrz_call(f"MODSINCE:{since},MAX:250"):
                lid, call = f.get("app_qrzlog_logid", ""), f["call"].upper()
                band = f.get("band", "").lower() or band_of(float(f.get("freq") or 0))
                mode = f.get("submode") or f.get("mode", "")
                country = f.get("country", "").title()
                ll = None
                if f.get("lat") and f.get("lon"):
                    def dm(s):
                        m = re.match(r"([NSEW])(\d{3}) ([\d.]+)", s, re.I)
                        return (-1 if m.group(1).upper() in "SW" else 1) * (int(m.group(2)) + float(m.group(3)) / 60) if m else None
                    a, o = dm(f["lat"]), dm(f["lon"])
                    ll = (a, o) if a is not None and o is not None else None
                ll = ll or grid_to_latlon(f.get("gridsquare"))
                is_conf = confirmed(f)
                if lid not in seen and announced < 10:
                    new_qso(call, band, mode, "QRZ", f.get("gridsquare", ""), ll and ll[0], ll and ll[1], country, f.get("state", ""))
                    announced += 1
                if is_conf and not seen.get(lid):
                    new_country = bool(country) and country not in countries
                    add_event({"type": "confirm", "call": call, "band": band, "mode": mode, "where": country,
                               "newCountry": new_country, "lat": ll and ll[0], "lon": ll and ll[1]})
                if is_conf and country:
                    countries.add(country)
                seen[lid] = is_conf
            state.update(seen=seen, countries=sorted(countries))
            json.dump(state, open(QRZ_STATE, "w"))
            time.sleep(QRZ_EVERY)
        except Exception as e:
            log.warning("QRZ: %s (trying again in 30 min)", e)
            time.sleep(1800)


def qrz_thread():
    while True:
        try:
            poll_qrz()
            return
        except Exception as e:
            log.warning("QRZ start-up: %s (trying again in 30 min)", e)
            time.sleep(1800)


# ---------------------------------------------------------------- test events
SAMPLES = {
    "qso": {"type": "qso", "call": "JA1XYZ", "band": "20m", "mode": "SSB", "src": "QRZ", "grid": "PM95",
            "lat": 35.7, "lon": 139.7, "where": "Japan"},
    "confirm": {"type": "confirm", "call": "ZS6ABC", "band": "15m", "mode": "FT8", "where": "South Africa",
                "newCountry": True, "lat": -26.2, "lon": 28.0},
}


# ---------------------------------------------------------------- web server
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WWW, **k)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass   # the clock asks every few seconds; keep the log quiet

    def send_page(self, path):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            body = b"<h1>Clock page not found</h1><p>Put index.html in the folder above the relay folder.</p>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/events":
            after = int((q.get("after") or ["-1"])[0])
            with lock:
                last = events[-1]["id"] if events else 0
                new = [e for e in events if e["id"] > after] if after >= 0 else []
                r = dict(rig) if rig and time.time() - rig.get("t", 0) < 20 else {}
            return self.send_json({"last": last, "events": new, "rig": r})
        if u.path == "/test":
            kind = (q.get("type") or ["qso"])[0]
            add_event(dict(SAMPLES.get(kind, SAMPLES["qso"]), test=True))
            return self.send_json({"ok": True, "sent": kind})
        if u.path in ("/", "/index.html") and not os.path.exists(os.path.join(WWW, "index.html")):
            return self.send_page(CLOCK_PAGE)   # only this one file from outside www, never relay.ini
        return super().do_GET()


def my_address():
    """This computer's address on the home network (no traffic is sent)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))
        return s.getsockname()[0]
    except OSError:
        return "<this computer's address>"


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    os.makedirs(WWW, exist_ok=True)
    for target in (listen_wsjtx, qrz_thread):
        threading.Thread(target=target, daemon=True).start()
    ip = my_address()
    log.info("clock relay on http://0.0.0.0:%s", PORT)
    log.info("OPEN THE CLOCK AT:  http://%s:%s/      (on this computer: http://localhost:%s/)", ip, PORT, PORT)
    log.info("FT8 program UDP setting:  %s  port %s      (leave this window open)", ip, WSJTX_PORT)
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
