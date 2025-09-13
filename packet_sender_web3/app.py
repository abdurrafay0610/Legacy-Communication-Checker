
from __future__ import annotations
import os, json, socket
from typing import Any, Dict, List
from pathlib import Path
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash

try:
    import backend.packet as packet  # type: ignore
except Exception:
    packet = None  # type: ignore

DATA_DIR = Path(os.environ.get("PACKET_SENDER_DATA_DIR","data"))
DEFS_PATH = DATA_DIR / "packets.json"

PACKET_VALIDATION_SCHEMES = getattr(packet, "PACKET_VALIDATION_SCHEMES", ["NONE","CHECKSUM","CRC16", "CRC32"])
PACKET_NAME_KEY = getattr(packet, "PACKET_NAME", "name")

def read_defs() -> List[Dict[str, Any]]:
    if not DEFS_PATH.exists():
        return []
    try:
        return json.loads(DEFS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def write_defs(items: List[Dict[str, Any]]) -> None:
    DEFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFS_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY","dev-secret")
    app.activity_log: List[Dict[str, Any]] = []

    @app.get("/")
    def home():
        return redirect(url_for("define_page"))

    @app.get("/define")
    def define_page():
        defs = read_defs()
        return render_template("define.html",
                               validation_schemes=PACKET_VALIDATION_SCHEMES,
                               packets=defs,
                               pkt_name_key=PACKET_NAME_KEY)

    @app.post("/api/define/preview")
    def api_define_preview():
        data = request.get_json(force=True, silent=True) or {}
        packet_name = data.get("packet_name","").strip()
        packet_size = int(data.get("packet_size") or 0)
        scheme = data.get("validation_scheme","")
        values_in = data.get("values") or {}
        if not packet_name or packet_size <= 0 or scheme not in PACKET_VALIDATION_SCHEMES:
            return jsonify({"ok": False, "error":"Invalid inputs"}), 400

        defs = read_defs()
        defs_by_name = {d.get(PACKET_NAME_KEY, d.get("name")): d for d in defs}

        values_out: Dict[int, Any] = {}
        for i in range(packet_size):
            spec = values_in.get(str(i)) or {}
            kind = spec.get("kind")
            if kind == "bytes":
                vals = spec.get("values") or []
                vals = [max(0, min(255, int(x))) for x in vals]
                values_out[i] = vals
            elif kind == "packet_ref":
                ref_name = spec.get("name","")
                ref = defs_by_name.get(ref_name)
                if not ref:
                    return jsonify({"ok": False, "error": f"Unknown packet '{ref_name}' for index {i}"}), 400
                values_out[i] = ref
            else:
                return jsonify({"ok": False, "error": f"Index {i} not configured"}), 400

        if packet and hasattr(packet, "define_packet"):
            try:
                defined = packet.define_packet(packet_name, values_out, scheme)  # type: ignore
            except Exception as e:
                return jsonify({"ok": False, "error": f"packet.define_packet() failed: {e}"}), 400
        else:
            defined = {
                PACKET_NAME_KEY: packet_name,
                "validation_scheme": scheme,
                "values": values_out,
                "size": packet_size
            }
        return jsonify({"ok": True, "definition": defined})

    @app.post("/api/define/save")
    def api_define_save():
        data = request.get_json(force=True, silent=True) or {}
        definition = data.get("definition")
        if not isinstance(definition, dict):
            return jsonify({"ok": False, "error": "No definition"}), 400

        if packet and hasattr(packet, "save_packet_definition"):
            try:
                packet.save_packet_definition(definition)  # type: ignore
            except Exception as e:
                return jsonify({"ok": False, "error": f"save_packet_definition failed: {e}"}), 400
        else:
            defs = read_defs()
            name = definition.get(PACKET_NAME_KEY) or definition.get("name")
            defs = [d for d in defs if (d.get(PACKET_NAME_KEY) or d.get("name")) != name]
            defs.append(definition)
            write_defs(defs)

        return jsonify({"ok": True})

    @app.get("/send")
    def send_page():
        defs = read_defs()
        return render_template("send.html",
                               packets=defs,
                               pkt_name_key=PACKET_NAME_KEY)

    @app.post("/api/send")
    def api_send():
        data = request.get_json(force=True, silent=True) or {}
        name = data.get("packet_name","")
        scheme = (data.get("scheme","") or "").upper()
        params = data.get("params") or {}

        defs = read_defs()
        selected = None
        for d in defs:
            if d.get(PACKET_NAME_KEY) == name or d.get("name") == name:
                selected = d
                break
        if not selected:
            return jsonify({"ok": False, "error":"Unknown packet"}), 400

        try:
            note = ""
            if packet and hasattr(packet, "send_packet"):
                try:
                    res = packet.send_packet(selected, scheme, **params)  # type: ignore
                    sent_bytes = int(res) if isinstance(res, int) else 0
                    return jsonify({"ok": True, "sent_bytes": sent_bytes, "notes":["packet.send_packet used"]})
                except Exception as e:
                    note = f"packet.send_packet failed: {e}"
            else:
                note = "No packet.send_packet — using generic sender"

            blob = compile_packet_to_bytes(selected)
            sent_bytes = 0
            if scheme == "UDP":
                host = params.get("host","127.0.0.1")
                port = int(params.get("port", 9000))
                sent_bytes = send_udp(host, port, blob)
            elif scheme == "TCP":
                host = params.get("host","127.0.0.1")
                port = int(params.get("port", 9000))
                timeout = float(params.get("timeout", 2.0))
                sent_bytes = send_tcp(host, port, blob, timeout)
            elif scheme == "SERIAL":
                try:
                    import serial  # type: ignore
                except Exception:
                    return jsonify({"ok": False, "error":"pyserial not installed"}), 400
                port_name = params.get("port","/dev/ttyUSB0")
                baud = int(params.get("baud", 115200))
                sent_bytes = send_serial(port_name, baud, blob)
            else:
                return jsonify({"ok": False, "error":"Unknown scheme"}), 400

            return jsonify({"ok": True, "sent_bytes": sent_bytes, "notes":[note]})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 400

    @app.get("/api/defs")
    def api_defs():
        return jsonify({"packets": read_defs(), "validation_schemes": PACKET_VALIDATION_SCHEMES, "name_key": PACKET_NAME_KEY})

    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    return app

def clamp_byte(x: int) -> int:
    return max(0, min(255, int(x)))

def compile_packet_to_bytes(defn: Dict[str, Any]) -> bytes:
    """
    Fallback compiler that turns a normalized saved definition into bytes.

    If user's packet module exposes a generator (e.g., build_bytes(def)), prefer that.
    Otherwise, we assume:
      defn["values"] = { index: [byte,...] OR nested_packet_dict }
    """
    try:
        if packet and hasattr(packet, "build_bytes"):
            return bytes(getattr(packet, "build_bytes")(defn))  # type: ignore
    except Exception:
        pass

    values = defn.get("values", {})
    out: List[int] = []
    keys = []
    for k in values.keys():
        try:
            keys.append(int(k))
        except Exception:
            keys.append(k)
    for idx in sorted(keys, key=lambda x: int(x)):
        v = values.get(str(idx), values.get(idx))
        if isinstance(v, dict) and ("values" in v or "size" in v or "validation_scheme" in v):
            out += list(compile_packet_to_bytes(v))
        elif isinstance(v, list):
            out += [clamp_byte(x) for x in v]
        else:
            continue
    return bytes(out)

def send_udp(host: str, port: int, blob: bytes) -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return s.sendto(blob, (host, port))
    finally:
        s.close()

def send_tcp(host: str, port: int, blob: bytes, timeout: float) -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.sendall(blob)
        return len(blob)
    finally:
        s.close()

def send_serial(port: str, baud: int, blob: bytes) -> int:
    import serial  # type: ignore
    with serial.Serial(port=port, baudrate=baud, timeout=2) as ser:  # type: ignore
        return ser.write(blob)

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","7860")), debug=True)
