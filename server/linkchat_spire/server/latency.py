"""Action timing without credentials, action payloads or player state."""
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("uvicorn.error.spire_latency")


class Timing:
    def __init__(self, action_id):
        self.action_id = str(action_id)
        self.started = time.perf_counter()
        self.values = {}

    @contextmanager
    def span(self, name):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.values[name] = self.values.get(name, 0) + (time.perf_counter() - start) * 1000

    def snapshot(self):
        return {**{key: round(value, 3) for key, value in self.values.items()},
                "total": round((time.perf_counter() - self.started) * 1000, 3)}

    def header(self):
        return ", ".join(f"{name};dur={value:.3f}" for name, value in self.snapshot().items())

    def log(self, outcome):
        logger.info("spire_action action_id=%s outcome=%s timing_ms=%s",
                    self.action_id, outcome, self.snapshot())
