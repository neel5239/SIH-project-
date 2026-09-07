from __future__ import annotations

from dataclasses import dataclass
from typing import Any


GUARDIAN_VERSION = "g-1.0"

DIAGNOSTIC_TERMS = {
    "diagnosis",
    "diagnosed",
    "diagnose",
    "disease",
    "disorder",
    "condition",
    "likely",
    "probable",
    "suggestive of",
    "consistent with",
}

THERAPEUTIC_TERMS = {
    "take",
    "prescribe",
    "prescription",
    "treatment",
    "treat",
    "therapy",
    "medication",
    "medicine",
    "dose",
    "dosage",
    "increase dose",
    "decrease dose",
    "start medication",
    "stop medication",
    "recommend",
    "recommended",
}


@dataclass(frozen=True)
class GuardianResult:
    label: str
    allowed: bool
    text: str
    reason: str
    version: str = GUARDIAN_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "allowed": self.allowed,
            "text": self.text,
            "reason": self.reason,
            "version": self.version,
        }


class GuardianError(RuntimeError):
    """Raised when the Guardian cannot safely evaluate content."""


class GuardianGate:
    """
    Deterministic M5 safety gate.

    Guardian labels generated clinical text as:
        clean
        diagnostic
        therapeutic

    Diagnostic and therapeutic content is blocked.

    Safety rule:
        Guardian failure -> fail closed.

    This implementation is intentionally conservative and deterministic.
    It does not diagnose patients or recommend treatment.
    """

    def __init__(
        self,
        *,
        version: str = GUARDIAN_VERSION,
    ):
        self.version = version
        self.outputs_checked = 0
        self.blocked_diagnostic = 0
        self.blocked_therapeutic = 0

    def check(self, text: str) -> GuardianResult:
        self.outputs_checked += 1

        if not isinstance(text, str) or not text.strip():
            raise GuardianError(
                "Guardian cannot safely evaluate empty or invalid text"
            )

        normalized = self._normalize(text)

        therapeutic_match = self._find_term(
            normalized,
            THERAPEUTIC_TERMS,
        )

        if therapeutic_match is not None:
            self.blocked_therapeutic += 1

            return GuardianResult(
                label="therapeutic",
                allowed=False,
                text=text,
                reason=f"Therapeutic content detected: {therapeutic_match}",
                version=self.version,
            )

        diagnostic_match = self._find_term(
            normalized,
            DIAGNOSTIC_TERMS,
        )

        if diagnostic_match is not None:
            self.blocked_diagnostic += 1

            return GuardianResult(
                label="diagnostic",
                allowed=False,
                text=text,
                reason=f"Diagnostic content detected: {diagnostic_match}",
                version=self.version,
            )

        return GuardianResult(
            label="clean",
            allowed=True,
            text=text,
            reason="No blocked diagnostic or therapeutic content detected",
            version=self.version,
        )

    def check_or_fail_closed(self, text: str) -> GuardianResult:
        """
        Guardian wrapper used by the M5 pipeline.

        Any unexpected Guardian failure results in blocked output.
        """
        try:
            return self.check(text)
        except Exception as exc:
            self.outputs_checked += 1

            return GuardianResult(
                label="blocked",
                allowed=False,
                text="",
                reason=f"Guardian failure; output blocked: {exc}",
                version=self.version,
            )

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().strip().split())

    @staticmethod
    def _find_term(
        text: str,
        terms: set[str],
    ) -> str | None:
        # Prefer longer phrases so "start medication" is checked
        # before the shorter "medication" term.
        for term in sorted(terms, key=len, reverse=True):
            if term in text:
                return term

        return None

    def metrics(self) -> dict[str, Any]:
        blocked_total = (
            self.blocked_diagnostic
            + self.blocked_therapeutic
        )

        return {
            "guardian_version": self.version,
            "outputs_checked": self.outputs_checked,
            "blocked_diagnostic": self.blocked_diagnostic,
            "blocked_therapeutic": self.blocked_therapeutic,
            "blocked_total": blocked_total,
            "emitted_diagnostic": 0,
            "emitted_therapeutic": 0,
        }

    def reset_metrics(self) -> None:
        self.outputs_checked = 0
        self.blocked_diagnostic = 0
        self.blocked_therapeutic = 0
