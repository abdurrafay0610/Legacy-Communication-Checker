from __future__ import annotations
import os, json, socket, threading, time, uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
from flask import Flask, jsonify, render_template, request, redirect, url_for

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import packet as packet_module
except Exception:
    packet_module = None  # type: ignore

DATA_DIR  = Path(os.environ.get("PACKET_SENDER_DATA_DIR", "data"))
DEFS_PATH = DATA_DIR / "packets.json"
LOGS_DIR  = DATA_DIR / "logs"

PACKET_VALIDATION_SCHEMES = getattr(
    packet_module, "PACKET_VALIDATION_SCHEMES",
    ["CHECKSUM", "REVS_CHECKSUM", "CRC16_LSB_MSB", "CRC16_MSB_LSB", "CRC32_LSB_MSB", "CRC32_MSB_LSB"]
)
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

def upsert_def(definition: Dict[str, Any]) -> None:
    name = definition.get(PACKET_NAME_KEY) or definition.get("name", "")
    defs = read_defs()
    defs = [d for d in defs if (d.get(PACKET_NAME_KEY) or d.get("name")) != name]
    defs.append(definition)
    write_defs(defs)

def find_def(name: str) -> Optional[Dict[str, Any]]:
    for d in read_defs():
        if d.get(PACKET_NAME_KEY) == name or d.get("name") == name:
            return d
    return None

def write_log_line(session_id: str, line: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{session_id}.log"
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")


# ---------------------------------------------------------------------------
# Transport helpers
# ---------------------------------------------------------------------------

def clamp_byte(x) -> int:
    return max(0, min(255, int(x)))

def compile_packet_to_bytes(defn: Dict[str, Any]) -> bytes:
    values = defn.get("values", {})
    out: List[int] = []
    for idx in sorted(values.keys(), key=lambda k: int(k)):
        v = values[idx]
        if isinstance(v, dict):
            out += list(compile_packet_to_bytes(v))
        elif isinstance(v, list):
            out += [clamp_byte(x) for x in v]
    return bytes(out)

def build_blob(definition: Dict[str, Any], corrupt_indices: List[int]) -> bytes:
    if packet_module and hasattr(packet_module, "create_packet"):
        pkt_list = packet_module.create_packet(definition)
        if corrupt_indices:
            packet_module.corrupt_packet_at_indices(pkt_list, corrupt_indices)
        return bytes(pkt_list)
    else:
        return compile_packet_to_bytes(definition)


# ---------------------------------------------------------------------------
# Transport classes
# ---------------------------------------------------------------------------

class UDPTransport:
    def __init__(self, host: str, port: int, ack_timeout: float):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(ack_timeout)

    def send(self, blob: bytes) -> int:
        return self.sock.sendto(blob, (self.host, self.port))

    def recv(self, bufsize: int = 4096) -> Optional[bytes]:
        try:
            data, _ = self.sock.recvfrom(bufsize)
            return data
        except socket.timeout:
            return None

    def close(self):
        self.sock.close()


class TCPTransport:
    def __init__(self, host: str, port: int, ack_timeout: float):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(ack_timeout)
        self.sock.connect((host, port))

    def send(self, blob: bytes) -> int:
        self.sock.sendall(blob)
        return len(blob)

    def recv(self, bufsize: int = 4096) -> Optional[bytes]:
        try:
            return self.sock.recv(bufsize)
        except socket.timeout:
            return None

    def close(self):
        self.sock.close()


class SerialTransport:
    def __init__(self, port_name: str, baud: int, ack_timeout: float):
        import serial  # type: ignore
        self.ser = serial.Serial(port=port_name, baudrate=baud, timeout=ack_timeout)

    def send(self, blob: bytes) -> int:
        return self.ser.write(blob)

    def recv(self, bufsize: int = 4096) -> Optional[bytes]:
        data = self.ser.read(bufsize)
        return data if data else None

    def close(self):
        self.ser.close()


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

_sessions: Dict[str, Dict[str, Any]] = {}
_sessions_lock = threading.Lock()


def _validate_ack(received: bytes, ack_definition: Dict[str, Any]) -> bool:
    """
    Validate a received ACK against a packet definition.
    Checks length first, then verifies each single-value byte position matches.
    Multi-value positions are accepted as wildcards.
    """
    if not (packet_module and hasattr(packet_module, "get_flat_byte_indices")):
        return False

    flat = packet_module.get_flat_byte_indices(ack_definition)

    try:
        sample = build_blob(ack_definition, [])
    except Exception:
        return False

    if len(received) != len(sample):
        return False

    for entry in flat:
        idx          = entry["flat_index"]
        valid_values = entry["valid_values"]
        if idx >= len(received):
            return False
        # Only enforce strict match when there is exactly one allowed value
        if len(valid_values) == 1:
            if received[idx] != valid_values[0]:
                return False
    return True


def _run_session(session_id: str, config: Dict[str, Any], stop_event: threading.Event):
    tx_def          = config["tx_def"]
    corrupt_indices = config["corrupt_indices"]
    scheme          = config["scheme"]
    params          = config["params"]
    interval_ms     = config["interval_ms"]
    ack_def         = config.get("ack_def")
    ack_timeout     = config.get("ack_timeout", 2.0)

    def log(msg: str, level: str = "INFO"):
        entry = {"ts": datetime.utcnow().isoformat() + "Z", "level": level, "msg": msg}
        with _sessions_lock:
            _sessions[session_id]["log"].append(entry)
        write_log_line(session_id, f"[{level}] {msg}")

    # Open transport
    transport = None
    try:
        if scheme == "UDP":
            transport = UDPTransport(params["host"], int(params["port"]), ack_timeout)
        elif scheme == "TCP":
            transport = TCPTransport(params["host"], int(params["port"]), ack_timeout)
        elif scheme == "SERIAL":
            transport = SerialTransport(params["port_name"], int(params["baud"]), ack_timeout)
        else:
            log(f"Unknown scheme '{scheme}'", "ERROR")
            return
    except Exception as e:
        log(f"Transport open failed: {e}", "ERROR")
        return

    log(
        f"Session started — scheme={scheme} interval={interval_ms}ms "
        f"corrupt_indices={corrupt_indices} "
        f"ack={'yes (' + ack_def.get(PACKET_NAME_KEY,'?') + ')' if ack_def else 'none'}"
    )

    seq = 0
    while not stop_event.is_set():
        seq += 1

        # Build packet
        try:
            blob = build_blob(tx_def, corrupt_indices)
        except Exception as e:
            log(f"[seq={seq}] Packet build failed: {e}", "ERROR")
            stop_event.wait(interval_ms / 1000.0)
            continue

        # Send
        try:
            sent = transport.send(blob)
            label = "[CORRUPTED]" if corrupt_indices else "[VALID]"
            log(f"[seq={seq}] SENT {sent}B {label} hex={blob.hex(' ')}")
        except Exception as e:
            log(f"[seq={seq}] Send failed: {e}", "ERROR")
            stop_event.wait(interval_ms / 1000.0)
            continue

        # ACK
        if ack_def is not None:
            received = transport.recv()
            if received is None:
                log(
                    f"[seq={seq}] ACK TIMEOUT after {ack_timeout}s | "
                    f"sent={blob.hex(' ')}",
                    "WARN"
                )
            else:
                ok = _validate_ack(received, ack_def)
                if ok:
                    log(f"[seq={seq}] ACK OK | received={received.hex(' ')}")
                else:
                    log(
                        f"[seq={seq}] ACK INVALID | "
                        f"sent={blob.hex(' ')} | received={received.hex(' ')}",
                        "WARN"
                    )

        stop_event.wait(interval_ms / 1000.0)

    transport.close()
    log("Session stopped.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

    @app.get("/")
    def home():
        return redirect(url_for("define_page"))

    @app.get("/define")
    def define_page():
        return render_template("define.html",
                               validation_schemes=PACKET_VALIDATION_SCHEMES,
                               packets=read_defs(),
                               pkt_name_key=PACKET_NAME_KEY)

    @app.get("/send")
    def send_page():
        return render_template("send.html",
                               packets=read_defs(),
                               pkt_name_key=PACKET_NAME_KEY)

    # ------------------------------------------------------------------
    # Define API
    # ------------------------------------------------------------------

    @app.post("/api/define/preview")
    def api_define_preview():
        data        = request.get_json(force=True, silent=True) or {}
        packet_name = (data.get("packet_name") or "").strip()
        packet_size = int(data.get("packet_size") or 0)
        scheme      = data.get("validation_scheme", "")
        values_in   = data.get("values") or {}

        if not packet_name:
            return jsonify({"ok": False, "error": "Packet name is required"}), 400
        if packet_size <= 0:
            return jsonify({"ok": False, "error": "Packet size must be at least 1"}), 400
        if scheme not in PACKET_VALIDATION_SCHEMES:
            return jsonify({"ok": False, "error": f"Unknown validation scheme '{scheme}'"}), 400

        defs_by_name = {(d.get(PACKET_NAME_KEY) or d.get("name")): d for d in read_defs()}

        values_out: Dict[str, Any] = {}
        for i in range(packet_size):
            spec = values_in.get(str(i)) or {}
            kind = spec.get("kind")
            if kind == "bytes":
                vals = [max(0, min(255, int(x))) for x in (spec.get("values") or [])]
                values_out[str(i)] = vals
            elif kind == "packet_ref":
                ref_name = spec.get("name", "")
                ref = defs_by_name.get(ref_name)
                if not ref:
                    return jsonify({"ok": False, "error": f"Unknown packet '{ref_name}' for index {i}"}), 400
                values_out[str(i)] = ref
            else:
                return jsonify({"ok": False, "error": f"Index {i} has no configuration"}), 400

        definition = {
            PACKET_NAME_KEY:            packet_name,
            "Packet Validation Scheme": scheme,
            "values":                   values_out,
        }
        return jsonify({"ok": True, "definition": definition})

    @app.post("/api/define/save")
    def api_define_save():
        data       = request.get_json(force=True, silent=True) or {}
        definition = data.get("definition")
        if not isinstance(definition, dict):
            return jsonify({"ok": False, "error": "No definition provided"}), 400
        name = definition.get(PACKET_NAME_KEY) or definition.get("name", "")
        if not name:
            return jsonify({"ok": False, "error": "Definition has no name"}), 400
        upsert_def(definition)
        return jsonify({"ok": True})

    # ------------------------------------------------------------------
    # Packet byte index inspection
    # ------------------------------------------------------------------

    @app.get("/api/packet/indices/<packet_name>")
    def api_packet_indices(packet_name: str):
        defn = find_def(packet_name)
        if not defn:
            return jsonify({"ok": False, "error": f"Unknown packet '{packet_name}'"}), 400
        if packet_module and hasattr(packet_module, "get_flat_byte_indices"):
            flat = packet_module.get_flat_byte_indices(defn)
        else:
            blob = compile_packet_to_bytes(defn)
            flat = [{"flat_index": i, "valid_values": [b]} for i, b in enumerate(blob)]
        return jsonify({"ok": True, "indices": flat})

    # ------------------------------------------------------------------
    # Session API
    # ------------------------------------------------------------------

    @app.post("/api/session/start")
    def api_session_start():
        """
        Body:
        {
            "packet_name":     "MyPacket",
            "scheme":          "UDP"|"TCP"|"SERIAL",
            "params":          { "host":"127.0.0.1", "port":9000, ... },
            "interval_ms":     1000,
            "corrupt_indices": [0, 2],        // [] = send valid
            "ack_packet_name": "AckPacket",   // null = no ACK expected
            "ack_timeout":     2.0
        }
        """
        data            = request.get_json(force=True, silent=True) or {}
        tx_name         = data.get("packet_name", "")
        scheme          = (data.get("scheme") or "").upper()
        params          = data.get("params") or {}
        interval_ms     = int(data.get("interval_ms", 1000))
        corrupt_indices = [int(x) for x in (data.get("corrupt_indices") or [])]
        ack_name        = data.get("ack_packet_name") or None
        ack_timeout     = float(data.get("ack_timeout", 2.0))

        tx_def = find_def(tx_name)
        if not tx_def:
            return jsonify({"ok": False, "error": f"Unknown packet '{tx_name}'"}), 400

        ack_def = None
        if ack_name:
            ack_def = find_def(ack_name)
            if not ack_def:
                return jsonify({"ok": False, "error": f"Unknown ACK packet '{ack_name}'"}), 400

        session_id = str(uuid.uuid4())[:8]
        stop_event = threading.Event()
        config = {
            "tx_def":          tx_def,
            "corrupt_indices": corrupt_indices,
            "scheme":          scheme,
            "params":          params,
            "interval_ms":     interval_ms,
            "ack_def":         ack_def,
            "ack_timeout":     ack_timeout,
        }

        t = threading.Thread(target=_run_session, args=(session_id, config, stop_event), daemon=True)
        with _sessions_lock:
            _sessions[session_id] = {"thread": t, "stop": stop_event, "log": []}
        t.start()

        return jsonify({"ok": True, "session_id": session_id})

    @app.post("/api/session/stop")
    def api_session_stop():
        data       = request.get_json(force=True, silent=True) or {}
        session_id = data.get("session_id", "")
        with _sessions_lock:
            session = _sessions.get(session_id)
        if not session:
            return jsonify({"ok": False, "error": "Session not found"}), 404
        session["stop"].set()
        return jsonify({"ok": True})

    @app.get("/api/session/logs/<session_id>")
    def api_session_logs(session_id: str):
        with _sessions_lock:
            session = _sessions.get(session_id)
        if not session:
            return jsonify({"ok": False, "error": "Session not found"}), 404
        return jsonify({
            "ok":      True,
            "log":     session["log"][-500:],
            "stopped": session["stop"].is_set(),
        })

    # ------------------------------------------------------------------
    # Utility
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