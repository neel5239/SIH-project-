import base64
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sarvamai import SarvamAI

from .base import LanguageProvider


load_dotenv()


class SarvamProvider(LanguageProvider):
    PROVIDER_NAME = "sarvam"

    STT_MODEL = "saaras:v4"
    TRANSLATION_MODEL = "mayura:v1"
    TTS_MODEL = "bulbul:v3"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")

        if not self.api_key:
            raise ValueError(
                "SARVAM_API_KEY is not configured. "
                "Add it to the project .env file."
            )

        self.client = SarvamAI(
            api_subscription_key=self.api_key
        )

    def speech_to_text(
        self,
        audio_path: str,
        source_language: str | None = None,
    ) -> dict[str, Any]:
        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}"
            )

        with path.open("rb") as audio_file:
            response = self.client.speech_to_text.transcribe(
                file=audio_file,
                model=self.STT_MODEL,
                mode="transcribe",
            )

        data = self._to_dict(response)

        transcript = (
            data.get("transcript")
            or data.get("text")
            or ""
        )

        if not transcript.strip():
            raise RuntimeError(
                "Sarvam STT returned an empty transcript."
            )

        confidence = self._extract_confidence(data)

        return {
            "transcript": transcript,
            "language_code": (
                data.get("language_code")
                or source_language
            ),
            "provider": self.PROVIDER_NAME,
            "model": self.STT_MODEL,
            "mode": "online",
            "confidence": confidence,
            "raw_response": data,
        }

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> dict[str, Any]:
        if not text.strip():
            raise ValueError(
                "Translation text cannot be empty."
            )

        response = self.client.text.translate(
            input=text,
            source_language_code=source_language,
            target_language_code=target_language,
            model=self.TRANSLATION_MODEL,
        )

        data = self._to_dict(response)

        translated_text = (
            data.get("translated_text")
            or data.get("translation")
            or data.get("text")
            or ""
        )

        if not translated_text.strip():
            raise RuntimeError(
                "Sarvam translation returned empty text."
            )

        return {
            "translated_text": translated_text,
            "source_language_code": (
                data.get("source_language_code")
                or source_language
            ),
            "target_language_code": (
                data.get("target_language_code")
                or target_language
            ),
            "provider": self.PROVIDER_NAME,
            "model": self.TRANSLATION_MODEL,
            "mode": "online",
            "raw_response": data,
        }

    def text_to_speech(
        self,
        text: str,
        language: str,
    ) -> bytes:
        if not text.strip():
            raise ValueError(
                "TTS text cannot be empty."
            )

        response = self.client.text_to_speech.convert(
            text=text,
            language_code=language,
            speaker="shubh",
            model=self.TTS_MODEL,
        )

        data = self._to_dict(response)

        audios = data.get("audios")

        if not audios:
            raise RuntimeError(
                "Sarvam TTS returned no audio."
            )

        try:
            audio = base64.b64decode(audios[0])
        except Exception as exc:
            raise RuntimeError(
                "Failed to decode Sarvam TTS audio."
            ) from exc

        if not audio:
            raise RuntimeError(
                "Sarvam TTS returned empty audio."
            )

        return audio

    @staticmethod
    def _extract_confidence(
        data: dict[str, Any],
    ) -> float | None:
        """
        Extract confidence if Sarvam exposes one.

        Sarvam STT responses may not provide a single
        normalized confidence score, so None is valid.
        """

        confidence = data.get("confidence")

        if confidence is not None:
            try:
                return float(confidence)
            except (TypeError, ValueError):
                pass

        return None

    @staticmethod
    def _to_dict(response: Any) -> dict[str, Any]:
        if hasattr(response, "model_dump"):
            return response.model_dump()

        if hasattr(response, "dict"):
            return response.dict()

        if isinstance(response, dict):
            return response

        raise TypeError(
            f"Unsupported Sarvam response type: "
            f"{type(response).__name__}"
        )