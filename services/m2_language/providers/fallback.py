from typing import Any

from .base import LanguageProvider


class FallbackLanguageProvider(LanguageProvider):
    """
    Online-first language provider with offline fallback.

    The primary provider is attempted first.
    If it raises an exception, the fallback provider is used.

    This class intentionally does not modify either provider.
    """

    def __init__(
        self,
        primary: LanguageProvider,
        fallback: LanguageProvider,
    ):
        self.primary = primary
        self.fallback = fallback

        self.last_provider: str | None = None
        self.last_mode: str | None = None
        self.last_error: str | None = None

    def _record_success(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        self.last_provider = result.get("provider")
        self.last_mode = result.get("mode")
        self.last_error = None
        return result

    def _record_fallback(
        self,
        result: dict[str, Any],
        error: Exception,
    ) -> dict[str, Any]:
        self.last_provider = result.get("provider")
        self.last_mode = result.get("mode")
        self.last_error = str(error)

        # Preserve the fallback provider's normal response shape.
        # Add fallback metadata without changing existing fields.
        result["fallback_used"] = True
        result["fallback_reason"] = str(error)

        return result

    def speech_to_text(
        self,
        audio_path: str,
        source_language: str | None = None,
    ) -> dict[str, Any]:
        try:
            result = self.primary.speech_to_text(
                audio_path=audio_path,
                source_language=source_language,
            )

            return self._record_success(result)

        except Exception as primary_error:
            result = self.fallback.speech_to_text(
                audio_path=audio_path,
                source_language=source_language,
            )

            return self._record_fallback(
                result,
                primary_error,
            )

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> dict[str, Any]:
        try:
            result = self.primary.translate(
                text=text,
                source_language=source_language,
                target_language=target_language,
            )

            return self._record_success(result)

        except Exception as primary_error:
            result = self.fallback.translate(
                text=text,
                source_language=source_language,
                target_language=target_language,
            )

            return self._record_fallback(
                result,
                primary_error,
            )

    def text_to_speech(
        self,
        text: str,
        language: str,
    ) -> bytes:
        try:
            audio = self.primary.text_to_speech(
                text=text,
                language=language,
            )

            self.last_provider = "primary"
            self.last_mode = "online"
            self.last_error = None

            return audio

        except Exception as primary_error:
            audio = self.fallback.text_to_speech(
                text=text,
                language=language,
            )

            self.last_provider = "fallback"
            self.last_mode = "offline"
            self.last_error = str(primary_error)

            return audio

    def close(self) -> None:
        """
        Close both providers when they expose close().
        """
        primary_close = getattr(
            self.primary,
            "close",
            None,
        )

        fallback_close = getattr(
            self.fallback,
            "close",
            None,
        )

        if primary_close is not None:
            primary_close()

        if fallback_close is not None:
            fallback_close()