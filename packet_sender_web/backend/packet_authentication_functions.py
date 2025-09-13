# Place your existing packet_authentication_functions here.
import hashlib

def sign_packet(pkt, **kwargs):
    # Example: attach SHA256 digest header
    h = hashlib.sha256(pkt.payload.encode("utf-8")).hexdigest()
    pkt.headers["X-Signature"] = h
    return pkt

def hash_payload(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
