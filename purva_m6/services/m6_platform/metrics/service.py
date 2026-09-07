from collections import deque


class MetricsState:
    def __init__(self):
        self.outputs_checked = 0
        self.blocked_diagnostic = 0
        self.blocked_therapeutic = 0
        self.emitted_diagnostic = 0
        self.red_flags_fired = 0
        self.fhir_push_total = 0

        self.turn_latencies_ms = deque(maxlen=5000)

    def record_turn_latency(self, milliseconds: float):
        self.turn_latencies_ms.append(float(milliseconds))

    def latency_stats(self):
        values = sorted(self.turn_latencies_ms)

        if not values:
            return 0, 0

        def percentile(items, percentile):
            if len(items) == 1:
                return items[0]

            rank = (len(items) - 1) * percentile
            low = int(rank)
            high = min(low + 1, len(items) - 1)

            if low == high:
                return items[low]

            return items[low] + (
                items[high] - items[low]
            ) * (rank - low)

        return (
            percentile(values, 0.50),
            percentile(values, 0.95),
        )


metrics = MetricsState()
