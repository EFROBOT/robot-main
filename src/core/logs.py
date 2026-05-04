from collections import deque


class Logs:
    def __init__(self, maxlen=200):
        self.buffer = deque(maxlen=maxlen)

    def log(self, source, message):
        line = f"[{source}] {message}"
        self.buffer.append(line)
        print(line, flush=True)

    def get_lines(self):
        return list(self.buffer)
