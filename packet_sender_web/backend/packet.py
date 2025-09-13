# Place your existing packet implementation here.
# Example shape; replace with your real implementation.
class Packet:
    def __init__(self, destination: str, payload: str, headers=None):
        self.destination = destination
        self.payload = payload
        self.headers = headers or {}

    def send(self) -> int:
        # TODO: send via UDP/TCP/whatever your project supports
        # Return number of bytes 'sent'
        return len(self.payload.encode("utf-8"))
