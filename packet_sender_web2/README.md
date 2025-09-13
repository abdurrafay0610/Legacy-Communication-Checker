
# Packet Sender — Two-Page Web UI (Flask)

- **/define**: Create and manage packet definitions (template name, destination, port, protocol, payload, headers/auth JSON, timeout, retries).
- **/send**: Choose a saved definition, optionally override fields, send, and view activity logs.

## Run (dev)
```bash
cd packet_sender_web2
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py  # http://localhost:7860
```

## Wire your backend
Replace `backend/` files with your real modules (or update imports in `app.py`). 
Wire your true sending logic inside `api_send()` where noted.
