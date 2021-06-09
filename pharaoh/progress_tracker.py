from time import perf_counter
from typing import Optional


class ProgressTracker:
    LEARNING_RATE = 0.5

    def __init__(self):
        self.current_progress: float = 0.0
        self.last_update: float = perf_counter()
        self.assumed_rate: Optional[float] = None

    def update_progress(self, new_progress: float):
        update_time = perf_counter()
        progress_delta = new_progress - self.current_progress
        if progress_delta <= 0:
            return
        time_delta = update_time - self.last_update
        if time_delta <= 0:
            return
        latest_rate = progress_delta/time_delta

        if self.assumed_rate is None:
            self.assumed_rate = latest_rate
        else:
            self.assumed_rate = self.assumed_rate*(1-self.LEARNING_RATE) + latest_rate*self.LEARNING_RATE

        self.current_progress = new_progress
        self.last_update = update_time

    def estimated_completion_time(self):
        return self.last_update + (1-self.current_progress) * self.assumed_rate
