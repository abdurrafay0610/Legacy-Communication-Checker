# Minimal file writer, adapt/replace with your existing one.
from pathlib import Path

class FileWriter:
    def __init__(self, file_path: str):
        self.path = Path(file_path)

    def write_line(self, text: str):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(text + "\n")
