
# Replace/extend with your own functions.
import hashlib
def sign_packet(pkt, **kwargs):
    if pkt is None: 
        return pkt
    h = hashlib.sha256(pkt.payload.encode("utf-8")).hexdigest()
    pkt.headers["X-Signature"] = h
    return pkt
