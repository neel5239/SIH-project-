from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class CompletionDecision:
    complete: bool
    reason: str | None = None


class CompletionPolicy:
    """
    Phase 1 completion policy.

    Completion can happen when:
    - all currently available ontology questions are answered/skipped
    - the patient explicitly stops
    - the interview timeout is reached
    """

    def __init__(
        self,
        timeout_s: int = 8 * 60,
    ):
        self.timeout_s = timeout_s

    def evaluate(
        self,
        *,
        total_questions: int,
        questions_asked: int,
        started_at: datetime | None,
        active: bool = True,
        patient_stop: bool = False,
    ) -> CompletionDecision:

        if not active:
            return CompletionDecision(
                complete=True,
                reason="already_complete",
            )

        if patient_stop:
            return CompletionDecision(
                complete=True,
                reason="patient_stop",
            )

        if started_at is not None:
            now = datetime.now(timezone.utc)

            elapsed_s = (
                now - started_at
            ).total_seconds()

            if elapsed_s >= self.timeout_s:
                return CompletionDecision(
                    complete=True,
                    reason="timeout",
                )

        if (
            total_questions > 0
            and questions_asked >= total_questions
        ):
            return CompletionDecision(
                complete=True,
                reason="complete",
            )

        return CompletionDecision(
            complete=False,
            reason=None,
        )