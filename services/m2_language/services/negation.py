import re
from dataclasses import dataclass


@dataclass
class NegationResult:
    """
    Result of lightweight negation detection.
    """

    has_negation: bool
    matched_terms: list[str]


class NegationDetector:
    """
    Detects common linguistic negation patterns.

    This is intentionally lightweight.

    It provides a negation hint for downstream processing and
    does not attempt to determine clinical meaning.
    """

    DEFAULT_PATTERNS = [
        r"\bno\b",
        r"\bnot\b",
        r"\bnever\b",
        r"\bnone\b",
        r"\bwithout\b",
        r"\bdoesn't\b",
        r"\bdoesnt\b",
        r"\bdon't\b",
        r"\bdont\b",
        r"\bdidn't\b",
        r"\bdidnt\b",
        r"\bhaven't\b",
        r"\bhavent\b",
        r"\bhasn't\b",
        r"\bhasnt\b",
        r"\bhadn't\b",
        r"\bhadnt\b",
        r"\bcan't\b",
        r"\bcant\b",
        r"\bcannot\b",
        r"\bcouldn't\b",
        r"\bcouldnt\b",
        r"\bwon't\b",
        r"\bwont\b",
    ]

    def __init__(self, patterns: list[str] | None = None):
        self.patterns = patterns or self.DEFAULT_PATTERNS

    def detect(self, text: str) -> NegationResult:
        """
        Detect whether the text contains common negation markers.
        """

        if not text.strip():
            return NegationResult(
                has_negation=False,
                matched_terms=[],
            )

        matched_terms: list[str] = []

        for pattern in self.patterns:
            matches = re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            for match in matches:
                if match not in matched_terms:
                    matched_terms.append(match)

        return NegationResult(
            has_negation=bool(matched_terms),
            matched_terms=matched_terms,
        )