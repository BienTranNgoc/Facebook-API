import time


class CircuitOpen(Exception):
    pass


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, name, failure_threshold=5, recovery_seconds=30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.state = self.CLOSED
        self.failure_count = 0
        self.opened_at = 0

    def before_call(self):
        if self.state != self.OPEN:
            return
        if time.monotonic() - self.opened_at >= self.recovery_seconds:
            self.state = self.HALF_OPEN
            return
        raise CircuitOpen(f"{self.name} circuit is open")

    def record_success(self):
        self.state = self.CLOSED
        self.failure_count = 0
        self.opened_at = 0

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            self.opened_at = time.monotonic()
