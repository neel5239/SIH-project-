from dataclasses import dataclass, field
import re
from typing import Any


@dataclass
class FilledSlot:
    ontology_key: str
    value: Any
    confidence: float
    provenance_id: str | None = None
    answered_by: str = "self"
    input_mode: str = "voice"
    raw_text: str | None = None


@dataclass
class SlotFillResult:
    slots: list[FilledSlot] = field(default_factory=list)
    unrecognised: list[str] = field(default_factory=list)
    needs_clarification: bool = False


class SlotFiller:
    """
    Phase 1 deterministic slot filler.

    This is intentionally not an LLM yet.
    Phase 2 can replace the extraction backend while preserving
    the same result contract.
    """

    NEGATIVE_PATTERNS = [
        r"\bno\b",
        r"\bnot\b",
        r"\bnever\b",
        r"\bnone\b",
        r"\bwithout\b",
        r"\bdoesn't\b",
        r"\bdoesnt\b",
        r"\bdon't\b",
        r"\bdont\b",
        r"\bhaven't\b",
        r"\bhavent\b",
        r"\bhasn't\b",
        r"\bhasnt\b",
    ]

    def fill(
        self,
        question: dict[str, Any],
        text_english: str,
        *,
        provenance_id: str | None = None,
        negation_hint: bool = False,
        asr_confidence: float | None = None,
        answered_by: str = "self",
        input_mode: str = "voice",
        touch_selection: Any = None,
    ) -> SlotFillResult:

        question_id = question["id"]
        value_type = question.get("value_type", "text")

        if touch_selection is not None:
            value = touch_selection

            return SlotFillResult(
                slots=[
                    FilledSlot(
                        ontology_key=question_id,
                        value=value,
                        confidence=1.0,
                        provenance_id=provenance_id,
                        answered_by=answered_by,
                        input_mode="touch",
                        raw_text=text_english or None,
                    )
                ]
            )

        text = (text_english or "").strip()

        if not text:
            return SlotFillResult(
                slots=[],
                unrecognised=[],
                needs_clarification=True,
            )

        confidence = self._base_confidence(asr_confidence)

        if question_id == "general.chief_complaint":
            return self._fill_text(
                question_id,
                text,
                confidence,
                provenance_id,
                answered_by,
                input_mode,
            )

        if question_id == "hpi.duration":
            return self._fill_duration(
                question_id,
                text,
                confidence,
                provenance_id,
                answered_by,
                input_mode,
            )

        if question_id == "hpi.severity":
            return self._fill_severity(
                question_id,
                text,
                confidence,
                provenance_id,
                answered_by,
                input_mode,
            )

        if question_id == "hpi.associated_symptoms":
            return self._fill_text(
                question_id,
                text,
                confidence,
                provenance_id,
                answered_by,
                input_mode,
            )

        if question_id == "general.past_medical_history":
            return self._fill_text(
                question_id,
                text,
                confidence,
                provenance_id,
                answered_by,
                input_mode,
            )

        return self._fill_text(
            question_id,
            text,
            confidence,
            provenance_id,
            answered_by,
            input_mode,
        )

    def _fill_text(
        self,
        question_id: str,
        text: str,
        confidence: float,
        provenance_id: str | None,
        answered_by: str,
        input_mode: str,
    ) -> SlotFillResult:

        return SlotFillResult(
            slots=[
                FilledSlot(
                    ontology_key=question_id,
                    value=text,
                    confidence=confidence,
                    provenance_id=provenance_id,
                    answered_by=answered_by,
                    input_mode=input_mode,
                    raw_text=text,
                )
            ]
        )

    def _fill_duration(
        self,
        question_id: str,
        text: str,
        confidence: float,
        provenance_id: str | None,
        answered_by: str,
        input_mode: str,
    ) -> SlotFillResult:

        lowered = text.lower()

        patterns = [
            (
                r"\b(today|this morning|since today)\b",
                "today",
            ),
            (
                r"\b(2|two|3|three)\s*(day|days)\b",
                "two_to_three_days",
            ),
            (
                r"\b(one|1)\s*(week|weeks)\b",
                "one_week",
            ),
            (
                r"\b(one|1)\s*(month|months)\b",
                "one_month",
            ),
            (
                r"\b\d+\s*(month|months|year|years)\b",
                "longer",
            ),
            (
                r"\b(for|since)\s+\d+\s*(day|days)\b",
                "other_duration",
            ),
        ]

        for pattern, value in patterns:
            if re.search(pattern, lowered):
                return SlotFillResult(
                    slots=[
                        FilledSlot(
                            ontology_key=question_id,
                            value=value,
                            confidence=confidence,
                            provenance_id=provenance_id,
                            answered_by=answered_by,
                            input_mode=input_mode,
                            raw_text=text,
                        )
                    ]
                )

        return SlotFillResult(
            slots=[
                FilledSlot(
                    ontology_key=question_id,
                    value={
                        "key": "other",
                        "raw_text": text,
                    },
                    confidence=min(confidence, 0.70),
                    provenance_id=provenance_id,
                    answered_by=answered_by,
                    input_mode=input_mode,
                    raw_text=text,
                )
            ],
            needs_clarification=False,
        )

    def _fill_severity(
        self,
        question_id: str,
        text: str,
        confidence: float,
        provenance_id: str | None,
        answered_by: str,
        input_mode: str,
    ) -> SlotFillResult:

        match = re.search(
            r"\b(10|[0-9])\b",
            text,
        )

        if match:
            score = int(match.group(1))

            if 0 <= score <= 10:
                return SlotFillResult(
                    slots=[
                        FilledSlot(
                            ontology_key=question_id,
                            value=score,
                            confidence=confidence,
                            provenance_id=provenance_id,
                            answered_by=answered_by,
                            input_mode=input_mode,
                            raw_text=text,
                        )
                    ]
                )

        lowered = text.lower()

        word_scores = {
            "none": 0,
            "no pain": 0,
            "mild": 2,
            "moderate": 6,
            "severe": 8,
            "worst": 10,
            "very severe": 10,
        }

        for phrase, score in word_scores.items():
            if phrase in lowered:
                return SlotFillResult(
                    slots=[
                        FilledSlot(
                            ontology_key=question_id,
                            value=score,
                            confidence=confidence,
                            provenance_id=provenance_id,
                            answered_by=answered_by,
                            input_mode=input_mode,
                            raw_text=text,
                        )
                    ]
                )

        return SlotFillResult(
            slots=[
                FilledSlot(
                    ontology_key=question_id,
                    value={
                        "key": "other",
                        "raw_text": text,
                    },
                    confidence=min(confidence, 0.70),
                    provenance_id=provenance_id,
                    answered_by=answered_by,
                    input_mode=input_mode,
                    raw_text=text,
                )
            ],
            needs_clarification=True,
        )

    @staticmethod
    def _base_confidence(
        asr_confidence: float | None,
    ) -> float:
        if asr_confidence is None:
            return 0.90

        return max(
            0.0,
            min(1.0, float(asr_confidence)),
        )