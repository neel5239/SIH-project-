from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml


@dataclass
class RedFlagEvent:
    rule_id: str
    name: str
    severity: str
    action: str
    message_key: str
    notify: list[str]
    detector: str = "rule"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "severity": self.severity,
            "action": self.action,
            "message_key": self.message_key,
            "notify": list(self.notify),
            "detector": self.detector,
        }


class RedFlagEngine:
    """
    Deterministic Phase 3 red-flag engine.

    Safety architecture:
        rules are primary;
        an ML detector may raise a flag later;
        an ML detector must never suppress a rule-raised flag.

    The engine is intentionally independent of the dialogue manager.
    This lets us validate the clinical rule layer before wiring
    abort/escalation into the interview state machine.
    """

    def __init__(self, ontology_path: str | Path | None = None):
        if ontology_path is None:
            ontology_path = (
                Path(__file__).resolve().parent.parent
                / "ontology"
                / "red_flags.yaml"
            )

        self.ontology_path = Path(ontology_path)
        self.rules = self._load_rules()

    def _load_rules(self) -> list[dict[str, Any]]:
        if not self.ontology_path.exists():
            raise FileNotFoundError(
                f"Red-flag ontology does not exist: {self.ontology_path}"
            )

        with self.ontology_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        rules = data.get("rules", [])

        if not isinstance(rules, list):
            raise ValueError(
                f"'rules' must be a list in {self.ontology_path}"
            )

        for rule in rules:
            self._validate_rule(rule)

        return rules

    @staticmethod
    def _validate_rule(rule: Any) -> None:
        if not isinstance(rule, dict):
            raise ValueError("Each red-flag rule must be an object")

        required = [
            "id",
            "name",
            "severity",
            "action",
            "message_key",
            "notify",
        ]

        for field in required:
            if field not in rule:
                raise ValueError(
                    f"Red-flag rule is missing required field '{field}'"
                )

        if not isinstance(rule["id"], str):
            raise ValueError("Red-flag rule id must be a string")

        if not isinstance(rule["notify"], list):
            raise ValueError(
                f"'notify' must be a list for rule {rule['id']}"
            )

        if "all_of" not in rule and "any_of" not in rule:
            raise ValueError(
                f"Rule {rule['id']} must contain all_of or any_of"
            )

    def rule_count(self) -> int:
        return len(self.rules)

    def rule_ids(self) -> list[str]:
        return [rule["id"] for rule in self.rules]

    def evaluate(
        self,
        slots: dict[str, Any] | list[dict[str, Any]] | None = None,
        utterance: str | None = None,
    ) -> list[RedFlagEvent]:
        """
        Evaluate all deterministic rules.

        `slots` may be either:
          - {ontology_key: value}
          - [{"ontology_key": ..., "value": ...}, ...]

        The current utterance is also checked through a synthetic
        `__utterance__` field so that a safety signal is not dependent
        exclusively on slot extraction.
        """

        normalized_slots = self._normalize_slots(slots)

        if utterance:
            normalized_slots["__utterance__"] = utterance

        events: list[RedFlagEvent] = []

        for rule in self.rules:
            if self._rule_matches(rule, normalized_slots):
                events.append(
                    RedFlagEvent(
                        rule_id=rule["id"],
                        name=rule["name"],
                        severity=rule["severity"],
                        action=rule["action"],
                        message_key=rule["message_key"],
                        notify=tuple(rule["notify"]),
                        detector="rule",
                    )
                )

        return events

    def evaluate_with_ml(
        self,
        slots: dict[str, Any] | list[dict[str, Any]] | None = None,
        utterance: str | None = None,
        ml_events: list[RedFlagEvent] | None = None,
    ) -> list[RedFlagEvent]:
        """
        Combine deterministic rules with optional ML detections.

        IMPORTANT:
        - every rule event is retained;
        - ML may add events;
        - ML cannot remove/suppress a rule event.
        """

        rule_events = self.evaluate(
            slots=slots,
            utterance=utterance,
        )

        combined = list(rule_events)
        existing_ids = {event.rule_id for event in combined}

        for event in ml_events or []:
            if event.rule_id not in existing_ids:
                combined.append(event)

        return combined

    def _rule_matches(
        self,
        rule: dict[str, Any],
        slots: dict[str, Any],
    ) -> bool:
        if "all_of" in rule:
            if not self._conditions_all_match(
                rule["all_of"],
                slots,
            ):
                return False

        if "any_of" in rule:
            if not self._conditions_any_match(
                rule["any_of"],
                slots,
            ):
                return False

        return True

    def _conditions_all_match(
        self,
        conditions: list[Any],
        slots: dict[str, Any],
    ) -> bool:
        if not isinstance(conditions, list):
            return False

        return all(
            self._condition_matches(condition, slots)
            for condition in conditions
        )

    def _conditions_any_match(
        self,
        conditions: list[Any],
        slots: dict[str, Any],
    ) -> bool:
        if not isinstance(conditions, list):
            return False

        return any(
            self._condition_matches(condition, slots)
            for condition in conditions
        )

    def _condition_matches(
        self,
        condition: Any,
        slots: dict[str, Any],
    ) -> bool:
        if not isinstance(condition, dict):
            return False

        if "any_of" in condition:
            return self._conditions_any_match(
                condition["any_of"],
                slots,
            )

        if "all_of" in condition:
            return self._conditions_all_match(
                condition["all_of"],
                slots,
            )

        slot_key = condition.get("slot")

        if not isinstance(slot_key, str):
            return False

        value = slots.get(slot_key)

        if value is None:
            return False

        if "equals" in condition:
            return self._equals(
                value,
                condition["equals"],
            )

        if "in" in condition:
            return self._contains_any(
                value,
                condition["in"],
            )

        if "contains" in condition:
            return self._contains_any(
                value,
                [condition["contains"]],
            )

        if "contains_any" in condition:
            return self._contains_any(
                value,
                condition["contains_any"],
            )

        if "within_hours" in condition:
            return self._within_hours(
                value,
                condition["within_hours"],
            )

        if "less_than" in condition:
            return self._less_than(
                value,
                condition["less_than"],
            )

        return False

    @staticmethod
    def _normalize_slots(
        slots: dict[str, Any] | list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        if slots is None:
            return {}

        if isinstance(slots, dict):
            return dict(slots)

        normalized: dict[str, Any] = {}

        if isinstance(slots, list):
            for item in slots:
                if not isinstance(item, dict):
                    continue

                key = item.get("ontology_key")

                if isinstance(key, str):
                    normalized[key] = item.get("value")

        return normalized

    @classmethod
    def _flatten_values(cls, value: Any) -> list[Any]:
        if isinstance(value, (list, tuple, set)):
            flattened: list[Any] = []

            for item in value:
                flattened.extend(
                    cls._flatten_values(item)
                )

            return flattened

        return [value]

    @classmethod
    def _contains_any(
        cls,
        value: Any,
        candidates: list[Any],
    ) -> bool:
        values = cls._flatten_values(value)

        normalized_values = [
            str(item).strip().lower()
            for item in values
        ]

        normalized_candidates = [
            str(item).strip().lower()
            for item in candidates
        ]

        for current in normalized_values:
            for candidate in normalized_candidates:
                if current == candidate:
                    return True

                if candidate in current:
                    return True

        return False

    @classmethod
    def _equals(
        cls,
        value: Any,
        expected: Any,
    ) -> bool:
        if isinstance(value, bool) or isinstance(expected, bool):
            return value is expected

        return (
            str(value).strip().lower()
            == str(expected).strip().lower()
        )

    @staticmethod
    def _numeric(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _less_than(
        cls,
        value: Any,
        threshold: Any,
    ) -> bool:
        numeric_value = cls._numeric(value)
        numeric_threshold = cls._numeric(threshold)

        if (
            numeric_value is None
            or numeric_threshold is None
        ):
            return False

        return numeric_value < numeric_threshold

    @classmethod
    def _within_hours(
        cls,
        value: Any,
        hours: Any,
    ) -> bool:
        """
        Check whether an onset/duration value falls within
        the requested number of hours.

        Supports:
            6                  -> 6 hours
            "6 hours"          -> 6 hours
            "two hours ago"    -> 2 hours
            "about two hours ago" -> 2 hours
            "today"            -> within 24 hours
            "sudden"           -> immediate onset
            "suddenly"         -> immediate onset
            "just now"         -> immediate onset
            "this morning"     -> within 24 hours
        """

        threshold = cls._numeric(hours)

        if threshold is None:
            return False

        numeric_value = cls._numeric(value)

        if numeric_value is not None:
            return numeric_value <= threshold

        text = str(value).strip().lower()

        immediate_terms = {
            "sudden",
            "suddenly",
            "today",
            "just now",
            "now",
            "this morning",
        }

        if text in immediate_terms:
            return threshold >= 24

        number_words = {
            "zero": 0,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
        }

        # Handle phrases such as:
        # "two hours ago"
        # "about three hours ago"
        # "started suddenly two hours ago"
        hour_match = re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|"
            r"ten|eleven|twelve|\d+(?:\.\d+)?)\s+hours?\b",
            text,
        )

        if hour_match:
            token = hour_match.group(1)

            if token in number_words:
                value_hours = number_words[token]
            else:
                try:
                    value_hours = float(token)
                except ValueError:
                    return False

            return value_hours <= threshold

        # Handle numeric expressions such as "6 hours".
        if "hour" in text:
            digits = "".join(
                character
                for character in text
                if character.isdigit() or character == "."
            )

            if digits:
                try:
                    return float(digits) <= threshold
                except ValueError:
                    return False

        return False