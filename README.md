# 🧪 Legacy Communication Testing Tool

## 📌 Overview

**Legacy Communication Testing Tool** is a simulation-based testing utility designed to validate the communication behavior of legacy systems. These systems often communicate using **UDP** or **Serial (RS-232/RS-485)** protocols, which can be hard to test with modern infrastructure.

This tool simulates the expected communication behavior of counterpart devices, allowing seamless **functional testing**, **fault injection**, and **protocol conformance** verification.

---

## 🎯 Features

- ✅ Simulates **UDP** and **Serial** communication protocols.
- ✅ Supports configurable **packet definitions** with custom validation (e.g., checksum, CRC).
- ✅ Automates sending/receiving of byte sequences.
- ✅ Validates device response based on expected behaviors.
- ✅ Includes support for **nested packets** (packets within packets).
- ✅ CLI interface for test integration and scripting.

---

## 📦 Packet Definition Format

Packet definitions are stored as `.json` files and must follow a strict structure. These definitions are used to construct, send, and validate simulated communication packets.

### ✅ Required Fields

Each packet definition must contain:

| Field | Type | Description |
|-------|------|-------------|
| `"Packet Name"` | `string` | Name identifier for the packet. |
| `"Packet Validation Scheme"` | `string` | The checksum or validation type. Must be one of: `["CHECKSUM", "REVS_CHECKSUM", "CRC16_LSB_MSB", "CRC16_MSB_LSB"]` |
| `"values"` | `dict` | A dictionary where keys are index positions and values are one of the following: <br> • List of possible byte values <br> • Dict (to nest another sub-packet) |

### 📌 Example Packet Definition

```json
{
  "Packet Name": "Heartbeat",
  "Packet Validation Scheme": "CHECKSUM",
  "values": {
    "0": [0xAA],
    "1": [0x01, 0x02, 0x03],
    "2": [0xFF],
    "3": {
      "Packet Name": "SubPacket",
      "Packet Validation Scheme": "CHECKSUM",
      "values": {
        "0": [0x10],
        "1": [0x20, 0x21]
      }
    }
  }
}
```

### 🔎 Notes on Value Types

- `values[i]` can be:
  - A **list**: defines possible byte values at index `i`.
    - `'X'` (optional) can be used to denote full byte range [0–255].
  - A **nested dictionary**: defines a sub-packet at index `i`.

- Each packet is built by selecting one random value from each index's list. Sub-packets are processed recursively.

- The tool appends authentication bytes (e.g., checksum) based on the selected validation scheme.

---

## 🚀 Quick Start

```bash
# Simulate communication over UDP
python simulate.py --mode udp --ip 127.0.0.1 --port 9000 --send ./Packets\ Definition/Heartbeat.json

# Simulate communication over Serial
python simulate.py --mode serial --port COM3 --baudrate 9600 --send ./Packets\ Definition/Heartbeat.json
```

---

## 📂 Project Structure

```
legacy-comm-test-tool/
├── simulate.py                     # Entry point
├── packet_builder.py               # Packet creation logic
├── file_writter.py                 # File I/O and utilities
├── packet_authentication_functions.py  # Checksum/CRC logic
├── Packets Definition/            # JSON-based packet definitions
│   └── Heartbeat.json
└── README.md
```

---

## 🔄 Define Your Own Packet

You can define packets programmatically using:

```python
from packet_builder import define_packet, save_packet_definition

packet = define_packet(
    name="CustomPacket",
    values={0: [0x10], 1: [0x20, 0x30], 2: [0xFF]},
    packet_validation_scheme="CHECKSUM"
)

save_packet_definition(packet)
```

---

## 🧪 Health Check

All packets go through a health validation process to ensure:
- Proper structure and field types
- Valid checksum scheme
- Sub-packets (if any) are also well-formed

---

## 🛠 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss your ideas.

---

## 📄 License

MIT License – see [LICENSE](LICENSE)
