import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from services.m2_language.providers.local import LocalProvider
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
    / "local_pipeline_cache"
)


def main():
    print()
    print("=" * 60)
    print("M2 REAL AI4BHARAT OFFLINE PIPELINE TEST")
    print("=" * 60)

    if not AUDIO_PATH.exists():
        raise FileNotFoundError(
            f"Test audio not found: {AUDIO_PATH}"
        )

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Clear only this test's cache.
    for cache_file in CACHE_DIR.glob("*.wav"):
        cache_file.unlink()

    provider = LocalProvider()

    pipeline = M2LanguagePipeline(
        provider=provider,
        tts_cache=TTSCache(
            cache_dir=str(CACHE_DIR)
        ),
    )

    # ---------------------------------------------------------
    # TEST 1: REAL AI4BHARAT OFFLINE INBOUND
    # ---------------------------------------------------------

    print()
    print("-" * 60)
    print("TEST 1: REAL AI4BHARAT OFFLINE INBOUND")
    print("-" * 60)

    start = time.perf_counter()

    result = pipeline.process_inbound(
        audio_path=str(AUDIO_PATH),
        source_language="hi-IN",
        target_language="en-IN",
    )

    duration = time.perf_counter() - start

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

    print()
    print(f"Inbound duration: {duration:.2f} seconds")

    assert result.transcript.strip()
    assert result.normalized_transcript.strip()
    assert result.translated_text.strip()

    assert result.provider == "ai4bharat"
    assert result.mode == "offline"

    print()
    print("REAL OFFLINE INBOUND: PASSED")

    # ---------------------------------------------------------
    # TEST 2: REAL AI4BHARAT OFFLINE OUTBOUND
    # ---------------------------------------------------------

    print()
    print("-" * 60)
    print("TEST 2: REAL AI4BHARAT OFFLINE OUTBOUND")
    print("-" * 60)

    question = "Do you have fever?"

    print()
    print("English question:")
    print(question)

    start = time.perf_counter()

    outbound_1 = pipeline.process_outbound(
        text=question,
        target_language="hi-IN",
        source_language="en-IN",
    )

    duration = time.perf_counter() - start

    print()
    print("Hindi translation:")
    print(outbound_1.translated_text)

    print()
    print("Audio size:")
    print(len(outbound_1.audio), "bytes")

    print()
    print("Provider:")
    print(outbound_1.provider)

    print()
    print("Model:")
    print(outbound_1.model)

    print()
    print("Mode:")
    print(outbound_1.mode)

    print()
    print("Cache hit:")
    print(outbound_1.cache_hit)

    print()
    print(f"Outbound duration: {duration:.2f} seconds")

    assert outbound_1.translated_text.strip()
    assert outbound_1.audio

    assert outbound_1.provider == "ai4bharat"
    assert outbound_1.mode == "offline"

    audio_path = (
        PROJECT_ROOT
        / "services"
        / "m2_language"
        / "tests"
        / "audio"
        / "local_pipeline_test.wav"
    )

    audio_path.write_bytes(outbound_1.audio)

    print()
    print("Saved audio:")
    print(audio_path)

    print()
    print("REAL OFFLINE OUTBOUND: PASSED")

    # ---------------------------------------------------------
    # TEST 3: OFFLINE TTS CACHE
    # ---------------------------------------------------------

    print()
    print("-" * 60)
    print("TEST 3: REAL AI4BHARAT TTS CACHE")
    print("-" * 60)

    start = time.perf_counter()

    outbound_2 = pipeline.process_outbound(
        text=question,
        target_language="hi-IN",
        source_language="en-IN",
    )

    duration = time.perf_counter() - start

    print()
    print("Second request cache hit:")
    print(outbound_2.cache_hit)

    print()
    print("Audio bytes identical:")
    print(outbound_1.audio == outbound_2.audio)

    print()
    print(f"Cached request duration: {duration:.4f} seconds")

    assert outbound_2.cache_hit is True
    assert outbound_1.audio == outbound_2.audio

    print()
    print("REAL OFFLINE CACHE: PASSED")

    pipeline.close()

    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("REAL AI4BHARAT OFFLINE M2 PIPELINE TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()