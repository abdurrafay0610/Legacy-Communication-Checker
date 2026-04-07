from __future__ import annotations
import os, json, socket
from typing import Any, Dict, List
from pathlib import Path
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash

# Root-level backend — packet.py and packet_authentication_functions.py
# sit one level above the web3 folder in the project root.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import packet as packet_module
except Exception:
    packet_module = None  # type: ignore

DATA_DIR = Path(os.environ.get("PACKET_SENDER_DATA_DIR", "data"))
DEFS_PATH = DATA_DIR / "packets.json"

PACKET_VALIDATION_SCHEMES = getattr(packet_module, "PACKET_VALIDATION_SCHEMES",
                                    ["CHECKSUM", "REVS_CHECKSUM", "CRC16_LSB_MSB",
                                     "CRC16_MSB_LSB", "CRC32_LSB_MSB", "CRC32_MSB_LSB"])
PACKET_NAME_KEY = getattr(packet_module, "PACKET_NAME", "Packet Name")


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Transport helpers
# ---------------------------------------------------------------------------

def clamp_byte(x: int) -> int:
    return max(0, min(255, int(x)))


def compile_packet_to_bytes(defn: Dict[str, Any]) -> bytes:
    """
    Fallback compiler: flattens a saved packet definition into raw bytes
    when packet_module.create_packet() is not available.
    """
    values = defn.get("values", {})
    out: List[int] = []
    keys = sorted(values.keys(), key=lambda k: int(k))
    for idx in keys:
        v = values[idx]
        if isinstance(v, dict) and ("values" in v or "Packet Validation Scheme" in v):
            out += list(compile_packet_to_bytes(v))
        elif isinstance(v, list):
            out += [clamp_byte(x) for x in v]
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
    with serial.Serial(port=port, baudrate=baud, timeout=2) as ser:
        return ser.write(blob)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
    app.activity_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

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

    @app.get("/send")
    def send_page():
        defs = read_defs()
        return render_template("send.html",
                               packets=defs,
                               pkt_name_key=PACKET_NAME_KEY)

    # ------------------------------------------------------------------
    # Define API
    # ------------------------------------------------------------------

    @app.post("/api/define/preview")
    def api_define_preview():
        data = request.get_json(force=True, silent=True) or {}
        packet_name = data.get("packet_name", "").strip()
        packet_size = int(data.get("packet_size") or 0)
        scheme = data.get("validation_scheme", "")
        values_in = data.get("values") or {}

        if not packet_name or packet_size <= 0 or scheme not in PACKET_VALIDATION_SCHEMES:
            return jsonify({"ok": False, "error": "Invalid inputs"}), 400

        defs = read_defs()
        defs_by_name = {d.get(PACKET_NAME_KEY, d.get("name")): d for d in defs}

        values_out: Dict[int, Any] = {}
        for i in range(packet_size):
            spec = values_in.get(str(i)) or {}
            kind = spec.get("kind")
            if kind == "bytes":
                vals = [max(0, min(255, int(x))) for x in (spec.get("values") or [])]
                values_out[i] = vals
            elif kind == "packet_ref":
                ref_name = spec.get("name", "")
                ref = defs_by_name.get(ref_name)
                if not ref:
                    return jsonify({"ok": False, "error": f"Unknown packet '{ref_name}' for index {i}"}), 400
                values_out[i] = ref
            else:
                return jsonify({"ok": False, "error": f"Index {i} not configured"}), 400

        if packet_module and hasattr(packet_module, "define_packet"):
            try:
                defined = packet_module.define_packet(packet_name, values_out, scheme)
            except Exception as e:
                return jsonify({"ok": False, "error": f"packet.define_packet() failed: {e}"}), 400
        else:
            defined = {
                PACKET_NAME_KEY: packet_name,
                "Packet Validation Scheme": scheme,
                "values": values_out,
            }

        return jsonify({"ok": True, "definition": defined})

    @app.post("/api/define/save")
    def api_define_save():
        data = request.get_json(force=True, silent=True) or {}
        definition = data.get("definition")
        if not isinstance(definition, dict):
            return jsonify({"ok": False, "error": "No definition"}), 400

        if packet_module and hasattr(packet_module, "save_packet_definition"):
            try:
                packet_module.save_packet_definition(definition)
            except Exception as e:
                return jsonify({"ok": False, "error": f"save_packet_definition failed: {e}"}), 400
        else:
            defs = read_defs()
            name = definition.get(PACKET_NAME_KEY) or definition.get("name")
            defs = [d for d in defs if (d.get(PACKET_NAME_KEY) or d.get("name")) != name]
            defs.append(definition)
            write_defs(defs)

        return jsonify({"ok": True})

    # ------------------------------------------------------------------
    # Send API
    # ------------------------------------------------------------------

    @app.post("/api/send")
    def api_send():
        """
        Expected JSON body:
        {
            "packet_name": "MyPacket",
            "scheme":       "UDP" | "TCP" | "SERIAL",
            "valid":        true | false,       # true = valid packet, false = corrupted
            "params": {
                # UDP / TCP
                "host": "127.0.0.1",
                "port": 9000,
                "timeout": 2.0,                 # TCP only, seconds
                # SERIAL
                "port_name": "/dev/ttyUSB0",
                "baud": 115200
            }
        }
        """
        data = request.get_json(force=True, silent=True) or {}
        name   = data.get("packet_name", "")
        scheme = (data.get("scheme", "") or "").upper()
        valid  = bool(data.get("valid", True))   # default: send valid packet
        params = data.get("params") or {}

        # ---- locate the saved definition --------------------------------
        defs = read_defs()
        selected = None
        for d in defs:
            if d.get(PACKET_NAME_KEY) == name or d.get("name") == name:
                selected = d
                break
        if not selected:
            return jsonify({"ok": False, "error": f"Unknown packet '{name}'"}), 400

        # ---- build the packet bytes -------------------------------------
        try:
            if packet_module and hasattr(packet_module, "create_packet"):
                # create_packet returns a list of ints
                pkt_list = packet_module.create_packet(selected)

                if not valid:
                    # corrupt_packet mutates in-place and returns the same list
                    packet_module.corrupt_packet(pkt_list)

                blob = bytes(pkt_list)
                build_method = "packet.create_packet()"
            else:
                # Fallback: compile bytes directly from definition
                blob = compile_packet_to_bytes(selected)
                build_method = "compile_packet_to_bytes() [fallback]"
        except Exception as e:
            return jsonify({"ok": False, "error": f"Packet build failed: {e}"}), 400

        # ---- send over the chosen transport scheme ----------------------
        try:
            if scheme == "UDP":
                host = params.get("host", "127.0.0.1")
                port = int(params.get("port", 9000))
                sent_bytes = send_udp(host, port, blob)

            elif scheme == "TCP":
                host    = params.get("host", "127.0.0.1")
                port    = int(params.get("port", 9000))
                timeout = float(params.get("timeout", 2.0))
                sent_bytes = send_tcp(host, port, blob, timeout)

            elif scheme == "SERIAL":
                try:
                    import serial  # noqa: F401
                except ImportError:
                    return jsonify({"ok": False, "error": "pyserial not installed"}), 400
                port_name = params.get("port_name", "/dev/ttyUSB0")
                baud      = int(params.get("baud", 115200))
                sent_bytes = send_serial(port_name, baud, blob)

            else:
                return jsonify({"ok": False, "error": f"Unknown scheme '{scheme}'"}), 400

        except Exception as e:
            return jsonify({"ok": False, "error": f"Send failed: {e}"}), 400

        result = {
            "ok":          True,
            "packet_name": name,
            "scheme":      scheme,
            "valid":       valid,
            "sent_bytes":  sent_bytes,
            "bytes_hex":   blob.hex(" "),
            "build_method": build_method,
        }
        app.activity_log.append(result)
        return jsonify(result)

    # ------------------------------------------------------------------
    # Utility endpoints
    # ------------------------------------------------------------------

    @app.get("/api/defs")
    def api_defs():
        return jsonify({
            "packets":            read_defs(),
            "validation_schemes": PACKET_VALIDATION_SCHEMES,
            "name_key":           PACKET_NAME_KEY,
        })

    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "7860")), debug=True)