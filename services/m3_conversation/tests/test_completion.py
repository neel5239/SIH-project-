from datetime import datetime, timedelta, timezone

from services.m3_conversation.services.completion import (
    CompletionPolicy,
)


def test_not_complete_while_questions_remain():
    policy = CompletionPolicy()

    result = policy.evaluate(
        total_questions=10,
        questions_asked=5,
        started_at=datetime.now(timezone.utc),
    )

    assert result.complete is False
    assert result.reason is None


def test_complete_when_all_questions_are_answered():
    policy = CompletionPolicy()

    result = policy.evaluate(
        total_questions=10,
        questions_asked=10,
        started_at=datetime.now(timezone.utc),
    )

    assert result.complete is True
    assert result.reason == "complete"


def test_complete_when_patient_stops():
    policy = CompletionPolicy()

    result = policy.evaluate(
        total_questions=10,
        questions_asked=3,
        started_at=datetime.now(timezone.utc),
        patient_stop=True,
    )

    assert result.complete is True
    assert result.reason == "patient_stop"


def test_complete_after_timeout():
    policy = CompletionPolicy(
        timeout_s=480,
    )

    started_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=481)
    )

    result = policy.evaluate(
        total_questions=10,
        questions_asked=3,
        started_at=started_at,
    )

    assert result.complete is True
    assert result.reason == "timeout"