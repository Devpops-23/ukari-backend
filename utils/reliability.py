# utils/reliability.py

def calculate_reliability(traveler):
    total_deliveries = traveler.on_time_deliveries + traveler.late_deliveries

    if total_deliveries == 0:
        on_time_rate = 1.0
    else:
        on_time_rate = traveler.on_time_deliveries / total_deliveries

    cancellation_penalty = traveler.cancellation_count * 5
    flight_penalty = traveler.flight_cancel_count * 2
    late_penalty = traveler.late_deliveries * 3

    score = (on_time_rate * 100) - cancellation_penalty - flight_penalty - late_penalty

    return max(0, min(100, score))

from routers import traveler
from utils.reliability import calculate_reliability

traveler.reliability_score = calculate_reliability(traveler)

if traveler.reliability_score < 40:
    traveler.status = "suspended"
