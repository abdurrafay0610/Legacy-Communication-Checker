# 🧪 Legacy Communication Testing Tool

## 📌 Overview

**Legacy Communication Testing Tool** is a simulation-based testing utility for validating the communication behaviour of legacy embedded systems. These systems typically communicate over **UDP**, **TCP**, or **Serial (RS-232/RS-485)** using structured binary protocols.

The tool lets you define packet structures, build valid or deliberately corrupted packets, send them continuously over a chosen transport, and validate incoming ACK responses — logging every anomaly to disk.

---

## 🎯 Features

- ✅ Supports **UDP**, **TCP**, and **Serial** communication protocols
- ✅ Configurable **packet definitions** with nested sub-packets
- ✅ Full **validation scheme** support: CHECKSUM, REVS_CHECKSUM, CRC16 (LSB/MSB), CRC32 (LSB/MSB)
- ✅ **Targeted byte corruption** — choose exact byte indices to corrupt per send session
- ✅ **Continuous packet sending** with a configurable interval (default 1000ms)
- ✅ **ACK / response validation** — define which packet definition you expect back, with a configurable timeout
- ✅ Anomaly logging to disk (`data/logs/<session_id>.log`) and live in the browser UI
- ✅ Web UI (Flask) with a Define page and a Send page
- ✅ CLI interface for scripting and headless use

---

## 📦 Packet Definition Format

Packet definitions are stored as JSON and drive everything: building, sending, validating ACKs, and corruption targeting.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `"Packet Name"` | `string` | Unique name identifier |
| `"Packet Validation Scheme"` | `string` | One of the six supported schemes (see below) |
| `"values"` | `dict` | Keys are string index positions; values are byte lists or nested packet dicts |

### Supported Validation Schemes

| Scheme | Trailing bytes | Description |
|--------|---------------|-------------|
| `CHECKSUM` | 1 | Sum of all data bytes mod 256 |
| `REVS_CHECKSUM` | 1 | Bitwise NOT of the checksum (`~sum & 0xFF`) |
| `CRC16_LSB_MSB` | 2 | CRC-16/BUYPASS (poly `0x8005`), LSB first |
| `CRC16_MSB_LSB` | 2 | CRC-16/BUYPASS, MSB first |
| `CRC32_LSB_MSB` | 4 | CRC-32 (reflected poly `0xEDB88320`), LSB first |
| `CRC32_MSB_LSB` | 4 | CRC-32, MSB first |

> **Important:** The trailing validation bytes must be pre-allocated as zero-valued entries in the `values` dict. The tool writes the correct checksum/CRC into those reserved slots at build time.

### Example Packet Definition

```json
{
  "Packet Name": "Heartbeat",
  "Packet Validation Scheme": "CRC16_LSB_MSB",
  "values": {
    "0": [0xAA],
    "1": [0x01, 0x02, 0x03],
    "2": [0xFF],
    "3": {
      "Packet Name": "SubPacket",
      "Packet Validation Scheme": "CHECKSUM",
      "values": {
        "0": [0x10],
        "1": [0x20, 0x21],
        "2": [0x00]
      }
    },
    "4": [0x00],
    "5": [0x00]
  }
}
```

### Notes on Value Types

- `values[i]` is either a **list** of allowed byte values, or a **nested packet dict**.
- When building a packet, one value is randomly selected from each list.
- Sub-packets are expanded recursively and their bytes are inserted in-place.
- Validation bytes are appended after all data bytes are assembled.

---

## 🖥️ Web UI (packet_sender_web3)

The web interface is a two-page Flask app. It is the canonical interface for this tool.

### Define Page (`/define`)

1. Enter a packet name and size (number of byte indices).
2. Select a validation scheme.
3. For each index, choose either a list of byte values or a reference to another saved packet (for nesting).
4. Preview the assembled definition, then save it.

Saved packets appear in a list at the bottom and are available for nesting in other packets.

### Send Page (`/send`)

A 5-step guided flow:

**Step 1 — Choose Packet:** Select any saved packet definition to send.

**Step 2 — Packet Validity:** Toggle between valid and invalid.
- **Valid:** packet is built with correct validation bytes.
- **Invalid:** select specific byte indices to corrupt. Each selected byte is forced to `0xFF` (or `0x00` if its current value is already `0xFF`). Indices can be chosen from a visual chip list (populated from the packet definition) or typed in manually.

**Step 3 — Expected Response (ACK):** Optionally select a packet definition that represents the expected ACK from the other side, and set a timeout in seconds. If no ACK is expected, leave this as "None".

**Step 4 — Sending Scheme:** Choose UDP, TCP, or Serial.

**Step 5 — Parameters:** Fill in host/port (UDP, TCP) or port name/baud rate (Serial), and set the send interval in milliseconds (default: 1000ms).

Press **Start Sending** to begin. The session runs in a background thread. A live log panel shows each sent packet, received ACK result, timeout warnings, and errors. Press **Stop** to end the session.

### Run (dev)

```bash
cd packet_sender_web3
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py  # http://localhost:7860
```

### Run (Docker)

```bash
cd packet_sender_web3
docker build -t packet-sender .
docker run -p 7860:7860 packet-sender
```

---

## 💻 CLI Interface

The CLI (`app.py` at the project root) provides the same define and send workflow in a terminal menu.

```bash
python app.py
```

Options:
- `1` — Define a new packet (name, size, validation scheme, per-index values or sub-packet reference)
- `2` — Send a packet (choose transport, then choose a saved packet definition)
- `3` — Exit

---

## 📂 Project Structure

```
legacy-comm-test-tool/
│
├── app.py                              # CLI entry point
├── packet.py                           # Core packet logic
├── packet_authentication_functions.py  # Checksum / CRC calculations
├── file_writter.py                     # File and folder I/O utilities
│
├── Packets Definition/                 # JSON packet definitions (CLI)
│   └── *.json
│
└── packet_sender_web3/                 # Web UI (Flask) — active implementation
    ├── app.py                          # Flask routes + session management
    ├── requirements.txt
    ├── Dockerfile
    ├── templates/
    │   ├── define.html                 # Packet definition page
    │   └── send.html                   # Send / session page
    ├── static/
    │   └── styles.css
    └── data/
        ├── packets.json                # Saved packet definitions (web UI)
        └── logs/
            └── <session_id>.log        # Per-session anomaly logs
```

---

## 🔌 Web API Reference

### Define

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/define/preview` | Build and preview a definition without saving |
| `POST` | `/api/define/save` | Save a definition to `data/packets.json` |
| `GET`  | `/api/defs` | List all saved definitions |

### Packet Inspection

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/packet/indices/<name>` | Returns the flat ordered list of byte indices and their valid values for a saved packet. Used by the Send page to populate the corruption selector. |

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/session/start` | Start a continuous send session (returns `session_id`) |
| `POST` | `/api/session/stop` | Stop a running session |
| `GET`  | `/api/session/logs/<session_id>` | Poll the in-memory log for a session |

#### `/api/session/start` body

```json
{
    "packet_name":     "Heartbeat",
    "scheme":          "UDP",
    "params": {
        "host": "127.0.0.1",
        "port": 9000
    },
    "interval_ms":     1000,
    "corrupt_indices": [0, 2],
    "ack_packet_name": "HeartbeatAck",
    "ack_timeout":     2.0
}
```

- `corrupt_indices`: empty list `[]` = send valid packet; any indices listed = those bytes are corrupted.
- `ack_packet_name`: `null` = no ACK expected.

---

## 📋 Logging

Each session writes a timestamped log file to `data/logs/<session_id>.log`. Log entries cover:

- Session start parameters
- Every packet sent (sequence number, byte count, valid/corrupted label, hex bytes)
- ACK received and whether it matched the expected definition
- ACK timeout events (with the sent hex for cross-reference)
- Transport errors
- Session stop

---

## 🔄 Define Your Own Packet (Python API)

```python
import packet

definition = packet.define_packet(
    name="CustomPacket",
    values={
        "0": [0xAA],
        "1": [0x01, 0x02],
        "2": [0x00]          # reserved for CHECKSUM
    },
    packet_validation_scheme="CHECKSUM"
)

packet.save_packet_definition(definition)

# Build a valid instance
pkt = packet.create_packet(definition)   # list of ints

# Corrupt specific bytes before sending
packet.corrupt_packet_at_indices(pkt, [0])

# Inspect byte layout
indices = packet.get_flat_byte_indices(definition)
# [{"flat_index": 0, "valid_values": [0xAA]}, ...]
```

---

## 🛠 Contributing

Pull requests are welcome. For major changes please open an issue first.

---

## 📄 License

MIT License — see [LICENSE](LICENSE)