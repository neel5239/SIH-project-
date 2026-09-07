from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .branch_selector import BranchSelector
from .completion import CompletionPolicy
from .ontology_loader import OntologyLoader
from .red_flag_engine import RedFlagEngine
from .slot_filler import FilledSlot, SlotFiller


@dataclass
class InterviewState:
    session_id: str
    opd_type: str = "general"
    is_return_visit: bool = False
    proxy_mode: bool = False

    asked_keys: list[str] = field(default_factory=list)
    skipped_keys: list[str] = field(default_factory=list)

    slots: dict[str, FilledSlot] = field(default_factory=dict)

    questions_asked: int = 0
    started_at: datetime | None = None
    last_turn_at: datetime | None = None

    active: bool = True
    end_reason: str | None = None

    red_flag_events: list[dict[str, Any]] = field(default_factory=list)


class DialogueManager:
    """
    Phase 3 M3 dialogue engine.

    Responsibilities:
    - maintain interview state
    - select the next ontology question
    - process M2 English text
    - preserve provenance
    - support voice and touch input
    - apply completion policy
    - pass collected slots to adaptive branch selection
    - evaluate deterministic red-flag rules after every turn
    - abort and escalate immediately when a critical red flag fires
    """

    def __init__(
        self,
        ontology_loader: OntologyLoader | None = None,
        slot_filler: SlotFiller | None = None,
        branch_selector: BranchSelector | None = None,
        completion_policy: CompletionPolicy | None = None,
        red_flag_engine: RedFlagEngine | None = None,
    ):
        self.ontology_loader = ontology_loader or OntologyLoader()
        self.slot_filler = slot_filler or SlotFiller()
        self.branch_selector = branch_selector or BranchSelector()
        self.completion_policy = (
            completion_policy or CompletionPolicy()
        )
        self.red_flag_engine = red_flag_engine or RedFlagEngine()

        self.questions = self.ontology_loader.get_all_questions()

        self.sessions: dict[str, InterviewState] = {}

    def start_session(
        self,
        session_id: str,
        *,
        opd_type: str = "general",
        is_return_visit: bool = False,
        proxy_mode: bool = False,
    ) -> dict[str, Any]:

        if session_id in self.sessions:
            return self._start_response(
                self.sessions[session_id]
            )

        now = datetime.now(timezone.utc)

        state = InterviewState(
            session_id=session_id,
            opd_type=opd_type,
            is_return_visit=is_return_visit,
            proxy_mode=proxy_mode,
            started_at=now,
            last_turn_at=now,
        )

        self.sessions[session_id] = state

        return self._start_response(state)

    def set_proxy_mode(
        self,
        session_id: str,
        enabled: bool,
    ) -> dict[str, Any]:

        state = self._get_session(session_id)


        if not state.active:
            return {
                "proxy_mode": state.proxy_mode,
                "state": "complete",
            }

        state.proxy_mode = bool(enabled)

        return {
            "proxy_mode": state.proxy_mode,
            "state": "continue",
        }

    def process_turn(
        self,
        session_id: str,
        *,
        text_english: str = "",
        audio_provenance_ref: str | None = None,
        asr_confidence: float | None = None,
        negation_hint: bool = False,
        touch_selection: Any = None,
        answered_by: str = "self",
        input_mode: str = "voice",
    ) -> dict[str, Any]:

        state = self._get_session(session_id)
        if state.proxy_mode and answered_by == "self":
            answered_by = "proxy"

        if not state.active:
            return {
                "slots_filled": [],
                "next_question": None,
                "progress": self._progress(state),
                "red_flag": (
                    state.red_flag_events[-1]
                    if state.red_flag_events
                    else None
                ),
                "state": "complete",
            }

        current_question = self._current_question(state)

        if current_question is None:
            self._complete(
                state,
                "complete",
            )

            return {
                "slots_filled": [],
                "next_question": None,
                "progress": self._progress(state),
                "red_flag": None,
                "state": "complete",
            }

        fill_result = self.slot_filler.fill(
            current_question,
            text_english,
            provenance_id=audio_provenance_ref,
            negation_hint=negation_hint,
            asr_confidence=asr_confidence,
            answered_by=answered_by,
            input_mode=input_mode,
            touch_selection=touch_selection,
        )

        filled_slots: list[dict[str, Any]] = []

        for slot in fill_result.slots:
            state.slots[slot.ontology_key] = slot

            filled_slots.append(
                self._slot_to_dict(slot)
            )

        state.asked_keys.append(
            current_question["id"]
        )

        state.questions_asked += 1
        state.last_turn_at = datetime.now(timezone.utc)

        # ---------------------------------------------------------
        # RED-FLAG EVALUATION
        # ---------------------------------------------------------
        red_flag_events = self.red_flag_engine.evaluate(
            slots=self._slots_for_red_flag_engine(state),
            utterance=text_english,
        )

        if red_flag_events:
            events = [
                event.to_dict()
                for event in red_flag_events
            ]

            state.red_flag_events.extend(events)

            self._complete(
                state,
                "red_flag",
            )

            primary_event = events[0]

            return {
                "slots_filled": filled_slots,
                "next_question": None,
                "progress": self._progress(state),
                "red_flag": primary_event,
                "red_flags": events,
                "state": "aborted",
                "end_reason": "red_flag",
                "escalation": {
                    "action": "abort_and_escalate",
                    "message_en": (
                        "Please stay here. "
                        "A nurse is coming now."
                    ),
                    "message_hi": (
                        "????? ???? ?????? "
                        "???? ??? ? ??? ???"
                    ),
                    "notify": primary_event.get(
                        "notify",
                        [],
                    ),
                },
                "needs_clarification": (
                    fill_result.needs_clarification
                ),
            }

        # ---------------------------------------------------------
        # NORMAL COMPLETION
        # ---------------------------------------------------------
        completion = self.completion_policy.evaluate(
            total_questions=len(self.questions),
            questions_asked=state.questions_asked,
            started_at=state.started_at,
            active=state.active,
        )

        if completion.complete:
            self._complete(
                state,
                completion.reason or "complete",
            )

            return {
                "slots_filled": filled_slots,
                "next_question": None,
                "progress": self._progress(state),
                "red_flag": None,
                "state": "complete",
                "needs_clarification": (
                    fill_result.needs_clarification
                ),
            }

        next_question = self._select_next_question(state)

        if next_question is None:
            self._complete(
                state,
                "complete",
            )

            return {
                "slots_filled": filled_slots,
                "next_question": None,
                "progress": self._progress(state),
                "red_flag": None,
                "state": "complete",
                "needs_clarification": (
                    fill_result.needs_clarification
                ),
            }

        return {
            "slots_filled": filled_slots,
            "next_question": self._question_response(
                next_question
            ),
            "progress": self._progress(state),
            "red_flag": None,
            "state": "continue",
            "needs_clarification": (
                fill_result.needs_clarification
            ),
        }

    def skip(
        self,
        session_id: str,
    ) -> dict[str, Any]:

        state = self._get_session(session_id)

        if not state.active:
            return {
                "next_question": None,
                "progress": self._progress(state),
                "state": "complete",
            }

        current_question = self._current_question(state)

        if current_question is not None:
            state.skipped_keys.append(
                current_question["id"]
            )

            state.asked_keys.append(
                current_question["id"]
            )

            state.questions_asked += 1
            state.last_turn_at = datetime.now(timezone.utc)

        completion = self.completion_policy.evaluate(
            total_questions=len(self.questions),
            questions_asked=state.questions_asked,
            started_at=state.started_at,
            active=state.active,
        )

        if completion.complete:
            self._complete(
                state,
                completion.reason or "complete",
            )

            return {
                "next_question": None,
                "progress": self._progress(state),
                "state": "complete",
            }

        next_question = self._select_next_question(state)

        if next_question is None:
            self._complete(
                state,
                "complete",
            )

            return {
                "next_question": None,
                "progress": self._progress(state),
                "state": "complete",
            }

        return {
            "next_question": self._question_response(
                next_question
            ),
            "progress": self._progress(state),
            "state": "continue",
        }

    def end_session(
        self,
        session_id: str,
        reason: str = "patient_stop",
    ) -> dict[str, Any]:

        state = self._get_session(session_id)

        self._complete(
            state,
            reason,
        )

        duration_s = 0.0

        if state.started_at and state.last_turn_at:
            duration_s = (
                state.last_turn_at
                - state.started_at
            ).total_seconds()

        return {
            "slot_count": len(state.slots),
            "sections_covered": sorted(
                {
                    question.get("section")
                    for question in self.questions
                    if question["id"] in state.slots
                }
            ),
            "duration_s": duration_s,
        }

    def get_slots(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:

        state = self._get_session(session_id)

        return [
            self._slot_to_dict(slot)
            for slot in state.slots.values()
        ]

    def get_state(
        self,
        session_id: str,
    ) -> InterviewState:

        return self._get_session(session_id)

    def _current_question(
        self,
        state: InterviewState,
    ) -> dict[str, Any] | None:

        return self._select_next_question(state)

    def _select_next_question(
        self,
        state: InterviewState,
    ) -> dict[str, Any] | None:

        return self.branch_selector.select_next(
            self.questions,
            set(state.asked_keys),
            set(state.skipped_keys),
            state.slots,
        )

    def _slots_for_red_flag_engine(
        self,
        state: InterviewState,
    ) -> list[dict[str, Any]]:

        return [
            self._slot_to_dict(slot)
            for slot in state.slots.values()
        ]

    def _start_response(
        self,
        state: InterviewState,
    ) -> dict[str, Any]:

        question = self._current_question(state)

        return {
            "question": (
                self._question_response(question)
                if question
                else None
            ),
            "options": (
                question.get("options", [])
                if question
                else []
            ),
            "slot_keys": (
                [question["id"]]
                if question
                else []
            ),
            "progress": self._progress(state),
            "estimated_remaining_s": (
                max(
                    0,
                    (
                        len(self.questions)
                        - state.questions_asked
                    ) * 30,
                )
            ),
            "state": (
                "continue"
                if question
                else "complete"
            ),
        }

    @staticmethod
    def _question_response(
        question: dict[str, Any],
    ) -> dict[str, Any]:

        return {
            "id": question["id"],
            "text_en": question["text_en"],
            "options": question.get(
                "options",
                [],
            ),
            "slot_keys": [
                question["id"]
            ],
            "input_modes": question.get(
                "input_modes",
                ["voice", "touch"],
            ),
            "value_type": question.get(
                "value_type",
                "text",
            ),
        }

    def _progress(
        self,
        state: InterviewState,
    ) -> dict[str, Any]:

        total = len(self.questions)

        percent = (
            round(
                (
                    state.questions_asked
                    / total
                ) * 100
            )
            if total
            else 100
        )

        return {
            "section": self._current_section(state),
            "percent": percent,
            "questions_asked": state.questions_asked,
            "questions_total": total,
        }

    def _current_section(
        self,
        state: InterviewState,
    ) -> str | None:

        next_question = self._current_question(state)

        if next_question is None:
            return None

        return next_question.get(
            "section"
        )

    @staticmethod
    def _slot_to_dict(
        slot: FilledSlot,
    ) -> dict[str, Any]:

        return {
            "ontology_key": slot.ontology_key,
            "value": slot.value,
            "confidence": slot.confidence,
            "provenance_id": slot.provenance_id,
            "answered_by": slot.answered_by,
            "input_mode": slot.input_mode,
            "raw_text": slot.raw_text,
        }

    @staticmethod
    def _complete(
        state: InterviewState,
        reason: str,
    ) -> None:

        state.active = False
        state.end_reason = reason

    def _get_session(
        self,
        session_id: str,
    ) -> InterviewState:

        state = self.sessions.get(
            session_id
        )

        if state is None:
            raise KeyError(
                f"Session not found: {session_id}"
            )

        return state


