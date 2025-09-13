# Packet Sender — Exact 2‑Page GUI (Flask)

**Define page** (`/define`) mirrors your console flow:
- Name
- Packet Size
- Validation Scheme (from `packet.PACKET_VALIDATION_SCHEMES`)
- For each index: list of bytes (0–255) **or** nest another saved packet

Server builds `values[index] = [bytes]` or `values[index] = (another packet)`.
If available, it calls:
```python
packet.define_packet(packet_name, values, validation_scheme)
packet.save_packet_definition(definition)
```

**Send page** (`/send`):
- Pick saved packet
- Choose scheme: UDP / TCP / Serial
- Provide parameters and send
- If your backend exposes `packet.send_packet(defn, scheme, **params)`, we use it;
  otherwise a generic sender is used.

## Run
```bash
cd packet_sender_web3
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py  # http://localhost:7860
```
