from collections import deque
from pathlib import Path


class Logs:
    def __init__(self, maxlen=200):
        self.buffer = deque(maxlen=maxlen)
        self.log_file = Path(__file__).resolve().parents[2] / "data" / "logs" / "robot.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, source, message):
        line = f"[{source}] {message}"
        self.buffer.append(line)
        with self.log_file.open("a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
        print(line, flush=True)

    def get_lines(self):
        return list(self.buffer)
