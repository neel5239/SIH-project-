import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from services.m2_language.providers.sarvam import SarvamProvider
from services.m2_language.services.pipeline import M2LanguagePipeline
from services.m2_language.services.tts_cache import TTSCache


AUDIO_PATH = (
    PROJECT_ROOT
    / "services"
    / "m2_language"
    / "tests"
    / "audio"
    / "test_converted.wav"
)

CACHE_DIR = (
    PROJECT_ROOT
    / "services"
    / "m2_language"
    / "tests"
    / "audio"
    / "sarvam_pipeline_cache"
)


def main():
    print()
    print("=" * 60)
    print("M2 REAL SARVAM PIPELINE TEST")
    print("=" * 60)

    if not AUDIO_PATH.exists():
        raise FileNotFoundError(
            f"Test audio not found: {AUDIO_PATH}"
        )

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    provider = SarvamProvider()

    pipeline = M2LanguagePipeline(
        provider=provider,
        tts_cache=TTSCache(
            cache_dir=str(CACHE_DIR)
        ),
    )

    # ---------------------------------------------------------
    # TEST 1: REAL SARVAM INBOUND PIPELINE
    # ---------------------------------------------------------

    print()
    print("-" * 60)
    print("TEST 1: REAL SARVAM INBOUND")
    print("-" * 60)

    result = pipeline.process_inbound(
        audio_path=str(AUDIO_PATH),
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
    print("English translation:")
    print(result.translated_text)

    print()
    print("Provider:")
    print(result.provider)

    print()
    print("Model:")
    print(result.model)

    print()
    print("Mode:")
    print(result.mode)

    print()
    print("ASR confidence:")
    print(result.confidence)

    print()
    print("Negation hint:")
    print(result.negation_hint)

    assert result.transcript.strip()
    assert result.normalized_transcript.strip()
    assert result.translated_text.strip()

    assert result.provider == "sarvam"
    assert result.mode == "online"

    print()
    print("REAL SARVAM INBOUND: PASSED")

    # ---------------------------------------------------------
    # TEST 2: REAL SARVAM OUTBOUND PIPELINE
    # ---------------------------------------------------------

    print()
    print("-" * 60)
    print("TEST 2: REAL SARVAM OUTBOUND")
    print("-" * 60)

    question = (
        "Do you have fever?"
    )

    print()
    print("English question:")
    print(question)

    outbound_1 = pipeline.process_outbound(
        text=question,
        target_language="hi-IN",
        source_language="en-IN",
    )

    print()
    print("Hindi translation:")
    print(outbound_1.translated_text)

    print()
    print("Audio size:")
    print(len(outbound_1.audio), "bytes")

    print()
    print("Cache hit:")
    print(outbound_1.cache_hit)

    assert outbound_1.translated_text.strip()
    assert outbound_1.audio
    assert outbound_1.provider == "sarvam"
    assert outbound_1.mode == "online"

    audio_path = (
        PROJECT_ROOT
        / "services"
        / "m2_language"
        / "tests"
        / "audio"
        / "sarvam_pipeline_test.wav"
    )

    audio_path.write_bytes(outbound_1.audio)

    print()
    print("Saved audio:")
    print(audio_path)

    print()
    print("REAL SARVAM OUTBOUND: PASSED")

    # ---------------------------------------------------------
    # TEST 3: REAL SARVAM TTS CACHE
    # ---------------------------------------------------------

    print()
    print("-" * 60)
    print("TEST 3: REAL SARVAM TTS CACHE")
    print("-" * 60)

    outbound_2 = pipeline.process_outbound(
        text=question,
        target_language="hi-IN",
        source_language="en-IN",
    )

    print()
    print("Second request cache hit:")
    print(outbound_2.cache_hit)

    print()
    print("Audio bytes identical:")
    print(outbound_1.audio == outbound_2.audio)

    assert outbound_2.cache_hit is True
    assert outbound_1.audio == outbound_2.audio

    print()
    print("REAL SARVAM CACHE: PASSED")

    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    pipeline.close()

    print()
    print("=" * 60)
    print("REAL SARVAM M2 PIPELINE TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()