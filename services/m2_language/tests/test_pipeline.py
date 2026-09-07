import sys
import wave
from pathlib import Path
import math
import struct
import re


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from services.m2_language.providers.base import LanguageProvider
from services.m2_language.services.pipeline import M2LanguagePipeline
from services.m2_language.services.tts_cache import TTSCache


TEST_AUDIO = (
    Path(__file__).resolve().parent
    / "audio"
    / "pipeline_mock_input.wav"
)


class MockProvider(LanguageProvider):

    def __init__(self):
        self.stt_calls = 0
        self.translation_calls = 0
        self.tts_calls = 0

    def speech_to_text(
        self,
        audio_path: str,
        source_language: str | None = None,
    ) -> dict:

        self.stt_calls += 1

        return {
            "transcript": (
                "I have no fever and I take metformin."
            ),
            "language_code": source_language,
            "provider": "mock",
            "model": "mock-stt",
            "mode": "test",
            "confidence": 0.95,
        }

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> dict:

        self.translation_calls += 1

        protected_match = re.search(
            r"__PROTECTED_TERM_\d+__",
            text,
        )

        protected_token = (
            protected_match.group(0)
            if protected_match
            else "metformin"
        )

        if (
            source_language == "hi-IN"
            and target_language == "en-IN"
        ):
            translated = (
                "I have no fever and I take "
                f"{protected_token}."
            )

        elif (
            source_language == "en-IN"
            and target_language == "hi-IN"
        ):
            translated = (
                "मुझे बुखार नहीं है और मैं "
                f"{protected_token} "
                "लेता हूँ।"
            )

        else:
            translated = text

        return {
            "translated_text": translated,
            "source_language_code": source_language,
            "target_language_code": target_language,
            "provider": "mock",
            "model": "mock-nmt",
            "mode": "test",
        }

    def text_to_speech(
        self,
        text: str,
        language: str,
    ) -> bytes:

        self.tts_calls += 1

        return (
            b"RIFF"
            + b"\x00" * 8
            + b"WAVE"
            + text.encode("utf-8")
        )

    def close(self) -> None:
        pass


def create_test_audio() -> Path:

    TEST_AUDIO.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    sample_rate = 16000
    duration_seconds = 1.0
    amplitude = 8000

    frames = bytearray()

    for index in range(
        int(sample_rate * duration_seconds)
    ):

        sample = int(
            amplitude
            * math.sin(
                2
                * math.pi
                * 440
                * index
                / sample_rate
            )
        )

        frames.extend(
            struct.pack(
                "<h",
                sample,
            )
        )

    with wave.open(
        str(TEST_AUDIO),
        "wb",
    ) as audio_file:

        audio_file.setnchannels(1)
        audio_file.setsampwidth(2)
        audio_file.setframerate(sample_rate)
        audio_file.writeframes(frames)

    return TEST_AUDIO


def test_inbound_pipeline():

    print()
    print("=" * 60)
    print("TEST 1: INBOUND PIPELINE")
    print("=" * 60)

    provider = MockProvider()

    pipeline = M2LanguagePipeline(
        provider=provider,
    )

    audio_path = create_test_audio()

    result = pipeline.process_inbound(
        audio_path=str(audio_path),
        source_language="hi-IN",
        target_language="en-IN",
    )

    print()
    print("Transcript:")
    print(result.transcript)

    print()
    print("Normalized transcript:")
    print(result.normalized_transcript)

    print()
    print("Translated text:")
    print(result.translated_text)

    print()
    print("Negation hint:")
    print(result.negation_hint)

    print()
    print("Negation terms:")
    print(result.negation_terms)

    print()
    print("Provider:")
    print(result.provider)

    print()
    print("Mode:")
    print(result.mode)

    assert result.transcript
    assert result.normalized_transcript

    assert result.translated_text == (
        "I have no fever and I take metformin."
    )

    assert result.negation_hint is True
    assert "no" in result.negation_terms

    assert result.provider == "mock"
    assert result.mode == "test"
    assert result.confidence == 0.95

    assert provider.stt_calls == 1
    assert provider.translation_calls == 1

    print()
    print("Inbound pipeline assertions: PASSED")


def test_outbound_pipeline():

    print()
    print("=" * 60)
    print("TEST 2: OUTBOUND PIPELINE")
    print("=" * 60)

    provider = MockProvider()

    cache_dir = (
        Path("services")
        / "m2_language"
        / "tests"
        / "audio"
        / "pipeline_test_cache"
    )

    cache_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for cache_file in cache_dir.glob("*.wav"):
        cache_file.unlink()

    pipeline = M2LanguagePipeline(
        provider=provider,
        tts_cache=TTSCache(
            cache_dir=str(cache_dir)
        ),
    )

    source_text = "Do you take metformin?"

    print()
    print("Source question:")
    print(source_text)

    result_1 = pipeline.process_outbound(
        text=source_text,
        target_language="hi-IN",
        source_language="en-IN",
    )

    print()
    print("Translated question:")
    print(result_1.translated_text)

    print()
    print("Audio size:")
    print(len(result_1.audio))

    print()
    print("Cache hit on first request:")
    print(result_1.cache_hit)

    assert result_1.translated_text == (
        "मुझे बुखार नहीं है और मैं metformin लेता हूँ।"
    )

    assert result_1.audio.startswith(b"RIFF")
    assert b"WAVE" in result_1.audio[:16]
    assert result_1.cache_hit is False

    assert provider.translation_calls == 1
    assert provider.tts_calls == 1

    result_2 = pipeline.process_outbound(
        text=source_text,
        target_language="hi-IN",
        source_language="en-IN",
    )

    print()
    print("Cache hit on second request:")
    print(result_2.cache_hit)

    print()
    print("Audio bytes identical:")
    print(result_1.audio == result_2.audio)

    assert result_2.cache_hit is True
    assert result_1.audio == result_2.audio

    assert provider.translation_calls == 2
    assert provider.tts_calls == 1

    print()
    print("Outbound pipeline assertions: PASSED")


def main():

    test_inbound_pipeline()
    test_outbound_pipeline()

    print()
    print("=" * 60)
    print("M2 PIPELINE INTEGRATION TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()