from dataclasses import dataclass
import re


@dataclass
class NormalizationResult:
    """
    Result of code-mix normalization.
    """

    original_text: str
    normalized_text: str
    changes: list[str]


class CodeMixNormalizer:
    """
    Performs conservative normalization of ASR output.

    The normalizer:
    - removes repeated whitespace
    - fixes spacing before punctuation
    - preserves the patient's original words
    - does NOT translate
    - does NOT add words
    - does NOT interpret clinical meaning
    """

    def normalize(self, text: str) -> NormalizationResult:
        """
        Normalize formatting while preserving linguistic content.
        """

        if not text.strip():
            return NormalizationResult(
                original_text=text,
                normalized_text=text,
                changes=[],
            )

        normalized = text
        changes: list[str] = []

        # Collapse repeated whitespace.
        cleaned = re.sub(r"\s+", " ", normalized).strip()

        if cleaned != normalized:
            changes.append("normalized_whitespace")

        normalized = cleaned

        # Remove spaces before punctuation.
        cleaned = re.sub(
            r"\s+([,.!?;:])",
            r"\1",
            normalized,
        )

        if cleaned != normalized:
            changes.append("normalized_punctuation_spacing")

        normalized = cleaned

        return NormalizationResult(
            original_text=text,
            normalized_text=normalized,
            changes=changes,
        )