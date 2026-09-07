from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence


class PrakritiScorer:
    """
    Deterministic Prakriti scorer for M5.

    Important:
    - Scores are returned as proportions in the range 0.0-1.0.
    - The scorer does not diagnose or recommend treatment.
    - Only ayush.prakriti.* slots are considered.
    - Answer confidence reduces evidence contribution.
    - Provenance is preserved and deduplicated.
    """

    DOSHAS = ("vata", "pitta", "kapha")

    # Transparent, configurable lexical evidence.
    # These are evidence mappings, not diagnostic rules.
    TERM_WEIGHTS: Dict[str, Dict[str, float]] = {
        "vata": {
            "vata": 1.0,
            "irregular": 1.0,
            "variable": 0.8,
            "light": 0.8,
            "disturbed": 1.0,
            "dry": 0.8,
            "restless": 0.8,
            "quick": 0.6,
        },
        "pitta": {
            "pitta": 1.0,
            "strong": 1.0,
            "moderate": 0.7,
            "sharp": 0.8,
            "intense": 0.8,
            "warm": 0.7,
            "hot": 0.7,
            "irritable": 0.8,
        },
        "kapha": {
            "kapha": 1.0,
            "steady": 1.0,
            "slow": 0.8,
            "deep": 0.9,
            "prolonged": 0.8,
            "heavy": 0.8,
            "calm": 0.7,
        },
    }

    def score(self, answers: Sequence[Mapping[str, Any]]) -> "PrakritiResult":
        prakriti_answers = [
            answer
            for answer in answers
            if str(answer.get("ontology_key", "")).startswith("ayush.prakriti.")
        ]

        items_total = len(prakriti_answers)

        raw = {dosha: 0.0 for dosha in self.DOSHAS}
        provenance: List[str] = []
        usable = 0
        confidence_values: List[float] = []

        for answer in prakriti_answers:
            evidence = self._extract_evidence(answer)

            if not evidence:
                continue

            answer_confidence = self._safe_confidence(answer.get("confidence", 1.0))
            weight = self._safe_weight(answer.get("weight", 1.0))

            if weight <= 0:
                continue

            usable += 1
            confidence_values.append(answer_confidence)

            for dosha, contribution in evidence.items():
                raw[dosha] += contribution * weight * answer_confidence

            prov_id = answer.get("provenance_id")
            if prov_id:
                provenance.append(str(prov_id))

        total = sum(raw.values())

        if total > 0:
            proportions = {
                dosha: raw[dosha] / total
                for dosha in self.DOSHAS
            }
        else:
            proportions = {dosha: 0.0 for dosha in self.DOSHAS}

        avg_confidence = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.0
        )

        sorted_scores = sorted(
            proportions.values(),
            reverse=True,
        )

        top_two_separation = (
            sorted_scores[0] - sorted_scores[1]
            if len(sorted_scores) >= 2
            else 0.0
        )

        coverage = (
            usable / items_total
            if items_total > 0
            else 0.0
        )

        # Confidence is deliberately conservative.
        confidence = min(
            1.0,
            avg_confidence
            * min(1.0, usable / 5.0)
            * min(1.0, 0.5 + coverage),
        )

        provisional = (
            usable < 3
            or avg_confidence < 0.75
            or top_two_separation < 0.10
        )

        return PrakritiResult(
            vata=proportions["vata"],
            pitta=proportions["pitta"],
            kapha=proportions["kapha"],
            confidence=confidence,
            provisional=provisional,
            answered_questions=usable,
            items_total=items_total,
            provenance=list(dict.fromkeys(provenance)),
        )

    def _extract_evidence(
        self,
        answer: Mapping[str, Any],
    ) -> Dict[str, float]:
        value = answer.get("value")

        if value is None:
            return {}

        evidence = {dosha: 0.0 for dosha in self.DOSHAS}

        if isinstance(value, Mapping):
            for dosha in self.DOSHAS:
                raw_value = value.get(dosha)
                if isinstance(raw_value, (int, float)):
                    evidence[dosha] += max(0.0, float(raw_value))

            return {
                dosha: score
                for dosha, score in evidence.items()
                if score > 0
            }

        if isinstance(value, (list, tuple, set)):
            combined: Dict[str, float] = {}
            for item in value:
                item_evidence = self._match_terms(str(item))
                for dosha, score in item_evidence.items():
                    combined[dosha] = combined.get(dosha, 0.0) + score
            return combined

        return self._match_terms(str(value))

    def _match_terms(self, text: str) -> Dict[str, float]:
        normalized = text.strip().lower()

        if not normalized:
            return {}

        result: Dict[str, float] = {}

        for dosha, terms in self.TERM_WEIGHTS.items():
            score = 0.0

            for term, weight in terms.items():
                if term in normalized:
                    score = max(score, weight)

            if score > 0:
                result[dosha] = score

        return result

    @staticmethod
    def _safe_confidence(value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _safe_weight(value: Any) -> float:
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return 1.0


@dataclass
class PrakritiResult:
    vata: float
    pitta: float
    kapha: float
    confidence: float
    provisional: bool
    answered_questions: int
    items_total: int
    provenance: List[str] = field(default_factory=list)

    @property
    def dominant(self) -> str:
        scores = {
            "vata": self.vata,
            "pitta": self.pitta,
            "kapha": self.kapha,
        }

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        first, second = ranked[0], ranked[1]

        # M5 permits a compound dominant label when the
        # leading two doshas are sufficiently close.
        if first[1] - second[1] < 0.10 and second[1] > 0:
            return f"{first[0]}-{second[0]}"

        return first[0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vata": round(self.vata, 4),
            "pitta": round(self.pitta, 4),
            "kapha": round(self.kapha, 4),
            "dominant": self.dominant,
            "confidence": round(self.confidence, 4),
            "provisional": self.provisional,
            "items_answered": self.answered_questions,
            "items_total": self.items_total,
            "provenance": list(self.provenance),
        }
