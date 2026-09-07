from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func

from ..auth.service import require_roles
from ..db.session import get_db
from ..db.models import (
    SessionRow,
    CorrectionRow,
    TriageRow,
    AuditRow,
)
from ..metrics.service import metrics


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/guardian")
def guardian(
    user=Depends(require_roles("admin", "physician")),
):
    return {
        "outputs_checked": metrics.outputs_checked,
        "blocked_diagnostic": metrics.blocked_diagnostic,
        "blocked_therapeutic": metrics.blocked_therapeutic,
        "emitted_diagnostic": metrics.emitted_diagnostic,
        "version": "g-1.0",
    }


@router.get("/accuracy")
def accuracy(
    window: str = "7d",
    db=Depends(get_db),
    user=Depends(require_roles("admin", "physician")),
):
    window_map = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    duration = window_map.get(window, timedelta(days=7))
    since = datetime.now(timezone.utc) - duration

    corrections = (
        db.query(CorrectionRow)
        .filter(CorrectionRow.corrected_at >= since)
        .all()
    )

    by_section = {}
    by_source_module = {}

    for correction in corrections:
        section = correction.section or "unknown"
        source = correction.source_module or "unknown"

        by_section[section] = by_section.get(section, 0) + 1
        by_source_module[source] = (
            by_source_module.get(source, 0) + 1
        )

    sessions = (
        db.query(func.count(SessionRow.session_id))
        .filter(SessionRow.started_at >= since)
        .scalar()
    ) or 0

    total_corrections = len(corrections)

    correction_rate = (
        total_corrections / sessions
        if sessions
        else 0
    )

    return {
        "window": window,
        "summaries_or_sessions": sessions,
        "corrections": total_corrections,
        "correction_rate": round(correction_rate, 4),
        "by_section": by_section,
        "by_source_module": by_source_module,
        "trend": [],
    }


@router.get("/latency")
def latency(
    user=Depends(require_roles("admin", "physician")),
):
    p50, p95 = metrics.latency_stats()

    return {
        "turn_p50_ms": round(p50, 2),
        "turn_p95_ms": round(p95, 2),
        "by_stage": {
            "stt": None,
            "nmt": None,
            "dialogue": None,
            "tts": None,
        },
        "engine_mix": {
            "bhashini": 0,
            "local": 0,
        },
        "sample_count": len(metrics.turn_latencies_ms),
    }


@router.get("/throughput")
def throughput(
    db=Depends(get_db),
    user=Depends(require_roles("admin", "physician")),
):
    now = datetime.now(timezone.utc)

    start_of_day = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    sessions = (
        db.query(SessionRow)
        .filter(SessionRow.started_at >= start_of_day)
        .all()
    )

    sessions_today = len(sessions)

    completed = sum(
        1
        for session in sessions
        if session.state == "complete"
    )

    abandoned = sum(
        1
        for session in sessions
        if session.state == "aborted"
    )

    active = sum(
        1
        for session in sessions
        if session.state not in {"complete", "aborted"}
    )

    durations = []

    for session in sessions:
        if session.state != "complete":
            continue

        completion_event = (
            db.query(AuditRow)
            .filter(
                AuditRow.session_id == session.session_id,
                AuditRow.event_type == "summary_signed",
                AuditRow.created_at >= session.started_at,
            )
            .order_by(AuditRow.created_at.desc())
            .first()
        )

        if completion_event:
            duration = (
                completion_event.created_at - session.started_at
            ).total_seconds()

            if duration >= 0:
                durations.append(duration)

    avg_duration_s = (
        sum(durations) / len(durations)
        if durations
        else 0
    )

    completion_rate = (
        completed / sessions_today
        if sessions_today
        else 0
    )

    abandonment_rate = (
        abandoned / sessions_today
        if sessions_today
        else 0
    )

    red_flags = (
        db.query(func.count(TriageRow.entry_id))
        .filter(TriageRow.entered_at >= start_of_day)
        .scalar()
    ) or 0

    return {
        "sessions_today": sessions_today,
        "completed": completed,
        "abandoned": abandoned,
        "active": active,
        "avg_duration_s": round(avg_duration_s, 2),
        "completion_rate": round(completion_rate, 4),
        "abandonment_rate": round(abandonment_rate, 4),
        "red_flags_fired": red_flags,
    }
