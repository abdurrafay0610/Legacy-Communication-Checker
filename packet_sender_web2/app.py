
from __future__ import annotations

import os, json
from datetime import datetime
from typing import Any, Dict, List
from pathlib import Path

from flask import Flask, jsonify, render_template, request, redirect, url_for, flash

# Import user backend (adjust if names differ)
try:
    from backend.packet import Packet  # type: ignore
except Exception:
    Packet = None  # type: ignore

try:
    import backend.packet_authentication_functions as auth  # type: ignore
except Exception:
    auth = None  # type: ignore

try:
    from backend.file_writter import FileWriter  # type: ignore
except Exception:
    FileWriter = None  # type: ignore

DATA_DIR = Path(os.environ.get("PACKET_SENDER_DATA_DIR", "data"))
DEFS_PATH = DATA_DIR / "packets.json"

def _read_defs() -> List[Dict[str, Any]]:
    if not DEFS_PATH.exists():
        return []
    try:
        return json.loads(DEFS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def _write_defs(defs: List[Dict[str, Any]]) -> None:
    DEFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFS_PATH.write_text(json.dumps(defs, indent=2), encoding="utf-8")

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
    app.activity_log = []  # type: ignore[attr-defined]

    @app.route("/")
    def home():
        return redirect(url_for("define_page"))

    # ---------- Packet Definition UI ----------
    @app.get("/define")
    def define_page():
        pkts = _read_defs()
        return render_template("define.html", packets=pkts)

    @app.post("/define")
    def define_create():
        form = request.form
        name = form.get("name", "").strip()
        if not name:
            flash("Name is required", "error")
            return redirect(url_for("define_page"))
        packet = {
            "name": name,
            "destination": form.get("destination", "").strip(),
            "protocol": form.get("protocol", "UDP").strip() or "UDP",
            "port": int(form.get("port", "0") or 0),
            "payload": form.get("payload", ""),
            "headers": _safe_json(form.get("headers", "")),
            "auth": _safe_json(form.get("auth", "")),
            "timeout_ms": int(form.get("timeout_ms", "2000") or 2000),
            "retries": int(form.get("retries", "0") or 0),
        }
        defs = _read_defs()
        # prevent duplicate names
        if any(d.get("name") == name for d in defs):
            flash(f"A packet named '{name}' already exists.", "error")
            return redirect(url_for("define_page"))
        defs.append(packet)
        _write_defs(defs)
        flash("Packet saved.", "ok")
        return redirect(url_for("define_page"))

    @app.post("/define/delete")
    def define_delete():
        name = request.form.get("name", "").strip()
        defs = _read_defs()
        defs = [d for d in defs if d.get("name") != name]
        _write_defs(defs)
        flash("Packet deleted.", "ok")
        return redirect(url_for("define_page"))

    # ---------- Send UI ----------
    @app.get("/send")
    def send_page():
        pkts = _read_defs()
        return render_template("send.html", packets=pkts)

    @app.post("/api/send")
    def api_send():
        data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
        # Load selected template if given
        template_name = data.get("template")
        base = {}
        if template_name:
            for d in _read_defs():
                if d.get("name") == template_name:
                    base = d
                    break

        # Merge overrides
        merged = {
            "destination": data.get("destination", base.get("destination", "")),
            "protocol": data.get("protocol", base.get("protocol", "UDP")),
            "port": data.get("port", base.get("port", 0)),
            "payload": data.get("payload", base.get("payload", "")),
            "headers": data.get("headers", base.get("headers", {})) or {},
            "auth": data.get("auth", base.get("auth", {})) or {},
            "timeout_ms": data.get("timeout_ms", base.get("timeout_ms", 2000)),
            "retries": data.get("retries", base.get("retries", 0)),
        }

        timestamp = datetime.utcnow().isoformat() + "Z"
        result: Dict[str, Any] = {"ok": True, "sent_bytes": 0, "notes": [], "request": merged}

        # Adapter: adjust this to your real backend API
        try:
            dest = f"{merged['destination']}:{merged['port']}" if merged.get("port") else merged["destination"]
            pkt = None
            if Packet is not None:
                # Try a few constructor shapes
                try:
                    pkt = Packet(destination=dest, payload=merged["payload"], headers=merged["headers"])  # type: ignore
                except Exception:
                    try:
                        pkt = Packet(dest, merged["payload"])  # type: ignore
                    except Exception:
                        pkt = None

            if auth is not None and hasattr(auth, "sign_packet"):
                try:
                    pkt = auth.sign_packet(pkt, **(merged["auth"] or {}))  # type: ignore
                    result["notes"].append("Signed via auth.sign_packet")
                except Exception as e:
                    result["notes"].append(f"auth.sign_packet failed: {e}")

            sent = 0
            send_err = None
            if pkt is not None and hasattr(pkt, "send"):
                try:
                    # You can pass protocol/timeout/retries into your own send if supported
                    sent = pkt.send()
                except Exception as e:
                    send_err = str(e)
            elif Packet is not None and hasattr(Packet, "send"):
                try:
                    sent = Packet.send(pkt)  # type: ignore
                except Exception as e:
                    send_err = str(e)
            else:
                send_err = "No send() found. Wire your backend send here."

            if send_err:
                result["ok"] = False
                result["error"] = send_err
            else:
                result["sent_bytes"] = int(sent) if isinstance(sent, int) else 0

            # Optional file log
            if FileWriter is not None:
                try:
                    fw = FileWriter(file_path=os.environ.get("PACKET_SENDER_LOG", "packet_sender.log"))
                    fw.write_line(f"{timestamp} SENT {dest} bytes={result['sent_bytes']} payload={merged['payload']!r}")
                    result["notes"].append("Logged via FileWriter")
                except Exception as e:
                    result["notes"].append(f"FileWriter failed: {e}")
        except Exception as e:
            result = {"ok": False, "error": f"Unexpected error: {e}"}

        app.activity_log.append({"ts": timestamp, "result": result})  # type: ignore[attr-defined]
        return jsonify(result)

    @app.get("/api/logs")
    def api_logs():
        return jsonify({"logs": getattr(app, "activity_log", [])[-200:]})

    @app.get("/api/defs")
    def api_defs():
        return jsonify({"packets": _read_defs()})

    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    return app

def _safe_json(s: str):
    s = (s or "").strip()
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}
    
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "7860")), debug=True)
