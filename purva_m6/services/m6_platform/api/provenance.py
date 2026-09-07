from io import BytesIO
from uuid import UUID
from wave import Error as WaveError
import wave

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import ProvenanceRow
from ..auth.service import require_roles
from ..audit.service import audit
from ..storage.minio import client, get_bytes


router = APIRouter(prefix="/doctor", tags=["doctor-provenance"])


class ProvenanceCreateRequest(BaseModel):
    session_id: UUID
    kind: str
    audio: dict | None = None
    image: dict | None = None


def _audio_metadata(row: ProvenanceRow) -> dict:
    if not row.audio:
        raise HTTPException(
            status_code=404,
            detail="Audio provenance is not available",
        )

    object_key = row.audio.get("object_key")

    if not object_key:
        raise HTTPException(
            status_code=422,
            detail="Audio provenance has no object_key",
        )

    return row.audio


@router.post("/provenance", status_code=201)
def create_provenance(
    body: ProvenanceCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("physician", "nurse", "admin")),
):
    if body.audio is None and body.image is None:
        raise HTTPException(
            status_code=400,
            detail="At least one provenance source is required",
        )

    prov_id = UUID(str(__import__("uuid").uuid4()))
    from datetime import datetime, timezone

    row = ProvenanceRow(
        prov_id=prov_id,
        session_id=body.session_id,
        kind=body.kind,
        audio=body.audio,
        image=body.image,
        created_by=user["user_id"],
        created_at=datetime.now(timezone.utc),
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    audit(
        db,
        "provenance_created",
        actor_id=user["user_id"],
        resource_id=str(prov_id),
        session_id=row.session_id,
        metadata={"kind": row.kind},
    )

    return {
        "prov_id": str(row.prov_id),
        "session_id": str(row.session_id),
        "kind": row.kind,
        "audio": row.audio,
        "image": row.image,
        "created_at": row.created_at.isoformat(),
    }


@router.get("/provenance/{prov_id}")
def get_provenance(
    prov_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_roles("physician", "nurse", "admin")),
):
    row = db.get(ProvenanceRow, prov_id)

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Provenance not found",
        )

    audit(
        db,
        "provenance_viewed",
        actor_id=user["user_id"],
        resource_id=str(row.prov_id),
        session_id=row.session_id,
        metadata={"kind": row.kind},
    )

    return {
        "prov_id": str(row.prov_id),
        "session_id": str(row.session_id),
        "kind": row.kind,
        "audio": row.audio,
        "image": row.image,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat(),
    }


@router.get("/provenance/{prov_id}/replay")
def replay_provenance(
    prov_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_roles("physician", "admin")),
):
    row = db.get(ProvenanceRow, prov_id)

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Provenance not found",
        )

    audio = _audio_metadata(row)

    object_key = audio["object_key"]
    start_ms = audio.get("start_ms")
    end_ms = audio.get("end_ms")
    mime_type = audio.get("mime_type", "audio/wav")

    if start_ms is None or end_ms is None:
        raise HTTPException(
            status_code=422,
            detail="Audio provenance must contain start_ms and end_ms",
        )

    try:
        start_ms = int(start_ms)
        end_ms = int(end_ms)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail="start_ms and end_ms must be integers",
        ) from exc

    if start_ms < 0 or end_ms <= start_ms:
        raise HTTPException(
            status_code=422,
            detail="Invalid provenance time range",
        )

    bucket = "purva-audio"

    try:
        client.stat_object(bucket, object_key)
        source_bytes = get_bytes(bucket, object_key)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail="Provenance audio object not found",
        ) from exc

    if mime_type.lower() not in {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
    }:
        raise HTTPException(
            status_code=415,
            detail="Only WAV provenance replay is currently supported",
        )

    try:
        with wave.open(BytesIO(source_bytes), "rb") as source:
            frame_rate = source.getframerate()
            total_frames = source.getnframes()

            start_frame = int(start_ms * frame_rate / 1000)
            end_frame = int(end_ms * frame_rate / 1000)

            if start_frame >= total_frames:
                raise HTTPException(
                    status_code=416,
                    detail="Provenance start time exceeds audio duration",
                )

            end_frame = min(end_frame, total_frames)

            if end_frame <= start_frame:
                raise HTTPException(
                    status_code=416,
                    detail="Provenance range contains no audio",
                )

            source.setpos(start_frame)
            frames = source.readframes(end_frame - start_frame)

            output = BytesIO()

            with wave.open(output, "wb") as clipped:
                clipped.setnchannels(source.getnchannels())
                clipped.setsampwidth(source.getsampwidth())
                clipped.setframerate(frame_rate)
                clipped.setcomptype(
                    source.getcomptype(),
                    source.getcompname(),
                )
                clipped.writeframes(frames)

            clipped_bytes = output.getvalue()

    except HTTPException:
        raise
    except (WaveError, EOFError) as exc:
        raise HTTPException(
            status_code=415,
            detail="Provenance object is not a valid WAV file",
        ) from exc

    actual_end_ms = int(end_frame * 1000 / frame_rate)

    audit(
        db,
        "provenance_replayed",
        actor_id=user["user_id"],
        resource_id=str(row.prov_id),
        session_id=row.session_id,
        metadata={
            "kind": row.kind,
            "object_key": object_key,
            "start_ms": start_ms,
            "end_ms": actual_end_ms,
            "bytes_returned": len(clipped_bytes),
        },
    )

    return Response(
        content=clipped_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'inline; filename="provenance-{prov_id}.wav"',
            "X-Provenance-ID": str(prov_id),
            "X-Provenance-Start-MS": str(start_ms),
            "X-Provenance-End-MS": str(actual_end_ms),
        },
    )
