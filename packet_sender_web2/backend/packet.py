
# Replace with your real implementation.
class Packet:
    def __init__(self, destination: str, payload: str, headers=None):
        self.destination = destination
        self.payload = payload
        self.headers = headers or {}
    def send(self) -> int:
        # TODO: implement actual network send (UDP/TCP/etc.)
        return len(self.payload.encode("utf-8"))
