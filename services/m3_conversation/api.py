from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .services.dialogue_manager import DialogueManager


app = FastAPI(
    title="MediSaarthi M3 Conversation Engine",
    version="1.0.0",
    description="API layer for the MediSaarthi conversation engine.",
)


# ---------------------------------------------------------------------------
# Shared engine
# ---------------------------------------------------------------------------

dialogue_manager = DialogueManager()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class StartSessionRequest(BaseModel):
    session_id: str = Field(min_length=1)
    opd_type: str = "general"
    is_return_visit: bool = False
    proxy_mode: bool = False


class TurnRequest(BaseModel):
    text_english: str = ""
    audio_provenance_ref: str | None = None
    asr_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    negation_hint: bool = False
    touch_selection: Any = None
    answered_by: str = "self"
    input_mode: str = "voice"


class SkipRequest(BaseModel):
    pass


class EndSessionRequest(BaseModel):
    reason: str = "patient_stop"


class ProxyModeRequest(BaseModel):
    enabled: bool


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "MediSaarthi M3 Conversation Engine",
        "status": "ok",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
    }


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

@app.post("/start")
def start_session(request: StartSessionRequest) -> dict[str, Any]:
    return dialogue_manager.start_session(
        request.session_id,
        opd_type=request.opd_type,
        is_return_visit=request.is_return_visit,
        proxy_mode=request.proxy_mode,
    )


@app.post("/turn/{session_id}")
def process_turn(
    session_id: str,
    request: TurnRequest,
) -> dict[str, Any]:
    try:
        return dialogue_manager.process_turn(
            session_id,
            text_english=request.text_english,
            audio_provenance_ref=request.audio_provenance_ref,
            asr_confidence=request.asr_confidence,
            negation_hint=request.negation_hint,
            touch_selection=request.touch_selection,
            answered_by=request.answered_by,
            input_mode=request.input_mode,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@app.post("/skip/{session_id}")
def skip_question(session_id: str) -> dict[str, Any]:
    try:
        return dialogue_manager.skip(session_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@app.post("/end/{session_id}")
def end_session(
    session_id: str,
    request: EndSessionRequest,
) -> dict[str, Any]:
    try:
        return dialogue_manager.end_session(
            session_id,
            reason=request.reason,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Proxy mode
# ---------------------------------------------------------------------------

@app.post("/proxy/{session_id}")
def set_proxy_mode(
    session_id: str,
    request: ProxyModeRequest,
) -> dict[str, Any]:
    try:
        return dialogue_manager.set_proxy_mode(
            session_id,
            request.enabled,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Session state / slots
# ---------------------------------------------------------------------------

@app.get("/slots/{session_id}")
def get_slots(session_id: str) -> list[dict[str, Any]]:
    try:
        return dialogue_manager.get_slots(session_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@app.get("/state/{session_id}")
def get_state(session_id: str) -> dict[str, Any]:
    try:
        state = dialogue_manager.get_state(session_id)

        return {
            "session_id": state.session_id,
            "opd_type": state.opd_type,
            "is_return_visit": state.is_return_visit,
            "proxy_mode": state.proxy_mode,
            "asked_keys": state.asked_keys,
            "skipped_keys": state.skipped_keys,
            "questions_asked": state.questions_asked,
            "active": state.active,
            "end_reason": state.end_reason,
            "red_flag_events": state.red_flag_events,
        }

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------

@app.post("/resume/{session_id}")
def resume_session(session_id: str) -> dict[str, Any]:
    try:
        state = dialogue_manager.get_state(session_id)

        if not state.active:
            return {
                "session_id": session_id,
                "state": "complete",
                "end_reason": state.end_reason,
                "question": None,
                "progress": dialogue_manager._progress(state),
            }

        question = dialogue_manager._current_question(state)

        return {
            "session_id": session_id,
            "state": "continue",
            "question": (
                dialogue_manager._question_response(question)
                if question
                else None
            ),
            "progress": dialogue_manager._progress(state),
            "proxy_mode": state.proxy_mode,
        }

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Ontology / questions
# ---------------------------------------------------------------------------

@app.get("/ontology/questions")
def get_questions(
    section: str | None = None,
) -> list[dict[str, Any]]:
    if section:
        return dialogue_manager.ontology_loader.get_questions_for_section(
            section
        )

    return dialogue_manager.ontology_loader.get_all_questions()


@app.get("/ontology/questions/{question_id}")
def get_question(question_id: str) -> dict[str, Any]:
    question = dialogue_manager.ontology_loader.get_question(
        question_id
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail=f"Question not found: {question_id}",
        )

    return question