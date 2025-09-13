# Packet Sender — Web UI (Flask)

This is a thin Flask web layer that turns a console-based Packet Sender into a browser app.

## Run (dev)

```bash
cd packet_sender_web
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py  # runs on http://localhost:7860
```

## Wire your backend

Replace files in `backend/` with your own (or edit imports in `app.py`):
- `backend/packet.py` — must expose a `Packet` with a `send()` method (or adjust the adapter in `/api/send`).
- `backend/packet_authentication_functions.py` — optional helpers (e.g., `sign_packet`, `hash_payload`).
- `backend/file_writter.py` — optional `FileWriter` with a `write_line()` method.

Adjust the `api_send()` function in `app.py` as needed to call your actual interfaces.
