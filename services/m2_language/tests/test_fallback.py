from services.m2_language.providers.base import LanguageProvider
from services.m2_language.providers.fallback import (
    FallbackLanguageProvider,
)


class FakePrimaryProvider(LanguageProvider):
    def speech_to_text(
        self,
        audio_path: str,
        source_language: str | None = None,
    ):
        raise RuntimeError("Simulated Sarvam STT failure.")

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ):
        raise RuntimeError("Simulated Sarvam translation failure.")

    def text_to_speech(
        self,
        text: str,
        language: str,
    ) -> bytes:
        raise RuntimeError("Simulated Sarvam TTS failure.")


class FakeFallbackProvider(LanguageProvider):
    def speech_to_text(
        self,
        audio_path: str,
        source_language: str | None = None,
    ):
        return {
            "transcript": "offline transcript",
            "provider": "ai4bharat",
            "model": "test-model",
            "mode": "offline",
            "confidence": None,
        }

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ):
        return {
            "translated_text": "offline translation",
            "provider": "ai4bharat",
            "model": "test-model",
            "mode": "offline",
        }

    def text_to_speech(
        self,
        text: str,
        language: str,
    ) -> bytes:
        return b"offline-audio"


def test_stt_fallback():
    provider = FallbackLanguageProvider(
        primary=FakePrimaryProvider(),
        fallback=FakeFallbackProvider(),
    )

    result = provider.speech_to_text(
        audio_path="test.wav",
        source_language="hi-IN",
    )

    assert result["transcript"] == "offline transcript"
    assert result["provider"] == "ai4bharat"
    assert result["mode"] == "offline"
    assert result["fallback_used"] is True
    assert "Sarvam STT failure" in result["fallback_reason"]


def test_translation_fallback():
    provider = FallbackLanguageProvider(
        primary=FakePrimaryProvider(),
        fallback=FakeFallbackProvider(),
    )

    result = provider.translate(
        text="hello",
        source_language="en-IN",
        target_language="hi-IN",
    )

    assert result["translated_text"] == "offline translation"
    assert result["provider"] == "ai4bharat"
    assert result["mode"] == "offline"
    assert result["fallback_used"] is True


def test_tts_fallback():
    provider = FallbackLanguageProvider(
        primary=FakePrimaryProvider(),
        fallback=FakeFallbackProvider(),
    )

    audio = provider.text_to_speech(
        text="नमस्ते",
        language="hi-IN",
    )

    assert audio == b"offline-audio"
    assert provider.last_mode == "offline"
    assert provider.last_error is not None


def test_primary_success():
    class WorkingPrimary(FakePrimaryProvider):
        def translate(
            self,
            text: str,
            source_language: str,
            target_language: str,
        ):
            return {
                "translated_text": "online translation",
                "provider": "sarvam",
                "model": "mayura:v1",
                "mode": "online",
            }

    provider = FallbackLanguageProvider(
        primary=WorkingPrimary(),
        fallback=FakeFallbackProvider(),
    )

    result = provider.translate(
        text="hello",
        source_language="en-IN",
        target_language="hi-IN",
    )

    assert result["translated_text"] == "online translation"
    assert result["provider"] == "sarvam"
    assert result["mode"] == "online"
    assert "fallback_used" not in result


if __name__ == "__main__":
    test_stt_fallback()
    test_translation_fallback()
    test_tts_fallback()
    test_primary_success()

    print("M2 FALLBACK PROVIDER TESTS PASSED")