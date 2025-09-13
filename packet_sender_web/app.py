from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request

# --- Import your existing backend modules here ---
# They are expected to live in ./backend next to this app.
# If your module names differ, just update the imports below.
try:
    from backend.packet import Packet  # type: ignore
except Exception:
    Packet = None  # fallback when your file name or class differs

try:
    import backend.packet_authentication_functions as auth  # type: ignore
except Exception:
    auth = None  # fallback

try:
    from backend.file_writter import FileWriter  # type: ignore
except Exception:
    FileWriter = None  # fallback


def create_app() -> Flask:
    app = Flask(__name__)

    # In-memory store for a minimal activity log (replace with DB if needed)
    app.activity_log = []  # type: ignore[attr-defined]

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.post("/api/send")
    def api_send():
        """Send a packet using the user's backend code.
        Expected JSON body:
        {
            "destination": "127.0.0.1:9000",
            "payload": "hello",
            "headers": {"k": "v"},      # optional
            "auth": {"user": "..."}      # optional
        }
        """
        data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
        dest = data.get("destination", "")
        payload = data.get("payload", "")
        headers = data.get("headers") or {}
        auth_params = data.get("auth") or {}

        timestamp = datetime.utcnow().isoformat() + "Z"

        # ---- Hook into your existing modules ----
        # The generic adapter below tries its best to work with whatever
        # interface your current code uses. Adjust as needed.
        result: Dict[str, Any] = {"ok": True, "sent_bytes": 0, "notes": []}

        try:
            # Example: maybe you have a Packet class with fields
            pkt = None
            if Packet is not None:
                try:
                    pkt = Packet(destination=dest, payload=payload, headers=headers)  # type: ignore[call-arg, misc]
                except TypeError:
                    # Try a more generic constructor if your class differs
                    pkt = Packet(dest, payload)  # type: ignore[misc]

            # Example: maybe you authenticate/sign the packet
            if auth is not None and hasattr(auth, "sign_packet"):
                try:
                    pkt = auth.sign_packet(pkt, **auth_params)  # type: ignore[arg-type]
                    result["notes"].append("Packet signed via auth.sign_packet")
                except Exception as e:
                    result["notes"].append(f"auth.sign_packet failed: {e}")

            # Example: send function could be on Packet or a free function
            sent = 0
            send_err = None
            if pkt is not None and hasattr(pkt, "send"):
                try:
                    sent = pkt.send()  # type: ignore[call-arg]
                except Exception as e:
                    send_err = str(e)
            elif Packet is not None and hasattr(Packet, "send"):
                try:
                    sent = Packet.send(pkt)  # type: ignore[attr-defined]
                except Exception as e:
                    send_err = str(e)
            else:
                send_err = "No send() found. Please wire your backend send function here."

            if send_err:
                result["ok"] = False
                result["error"] = send_err
            else:
                result["sent_bytes"] = int(sent) if isinstance(sent, int) else 0

            # Optional: write an activity log using your FileWriter if it exists
            if FileWriter is not None:
                try:
                    fw = FileWriter(file_path=os.environ.get("PACKET_SENDER_LOG", "packet_sender.log"))
                    fw.write_line(f"{timestamp}  SENT  {dest}  bytes={result['sent_bytes']}  payload={payload!r}")
                    result["notes"].append("Logged via FileWriter")
                except Exception as e:
                    result["notes"].append(f"FileWriter failed: {e}")

        except Exception as e:
            result = {"ok": False, "error": f"Unexpected error: {e}"}

        # also add to in-memory activity log
        app.activity_log.append(
            {"timestamp": timestamp, "destination": dest, "payload": payload, "headers": headers, "result": result}
        )  # type: ignore[attr-defined]

        return jsonify(result)

    @app.get("/api/logs")
    def api_logs():
        # return latest 200 rows
        logs = getattr(app, "activity_log", [])[-200:]
        return jsonify({"logs": logs})

    @app.post("/api/auth/test")
    def api_auth_test():
        data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
        payload = data.get("payload", "")
        try:
            if auth is not None and hasattr(auth, "hash_payload"):
                digest = auth.hash_payload(payload)  # type: ignore[attr-defined]
            else:
                digest = "auth.hash_payload not found — wire your function here."
            return jsonify({"ok": True, "digest": digest})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 400

    @app.get("/api/health")
    def api_health():
        return jsonify({"ok": True, "ts": datetime.utcnow().isoformat() + "Z"})

    return app


if __name__ == "__main__":
    # For local dev only. In prod use gunicorn: `gunicorn -w 2 -b 0.0.0.0:7860 app:create_app()`
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "7860")), debug=True)
