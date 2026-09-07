import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from services.m2_language.providers.local import LocalProvider
from services.m2_language.services.tts_cache import TTSCache


TEXT = "नमस्ते, आपका स्वागत है।"
LANGUAGE = "hi-IN"

OUTPUT_PATH = (
    Path("services")
    / "m2_language"
    / "tests"
    / "audio"
    / "tts_cache_test.wav"
)


def main():
    print("=" * 60)
    print("M2 TTS CACHE INTEGRATION TEST")
    print("=" * 60)

    provider = LocalProvider()

    cache = TTSCache(
        cache_dir="services/m2_language/tests/audio/tts_cache_test"
    )

    try:
        print()
        print("TEST 1: First TTS request")
        print("Expected: cache MISS -> generate audio")

        start = time.perf_counter()

        audio_1 = cache.get_or_create(
            TEXT,
            LANGUAGE,
            provider.text_to_speech,
        )

        first_duration = time.perf_counter() - start

        print(f"First request duration: {first_duration:.2f} seconds")
        print(f"First audio size: {len(audio_1)} bytes")

        if not audio_1:
            raise RuntimeError(
                "First TTS request returned empty audio."
            )

        OUTPUT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        OUTPUT_PATH.write_bytes(audio_1)

        print(f"Test audio saved to:\n{OUTPUT_PATH}")

        cache_path = cache._cache_path(
            TEXT,
            LANGUAGE,
        )

        print()
        print("Cache path:")
        print(cache_path)

        if not cache_path.exists():
            raise RuntimeError(
                "Cache file was not created."
            )

        print("Cache file exists: YES")

        print()
        print("TEST 2: Same TTS request")
        print("Expected: cache HIT -> no TTS generation")

        start = time.perf_counter()

        audio_2 = cache.get_or_create(
            TEXT,
            LANGUAGE,
            provider.text_to_speech,
        )

        second_duration = time.perf_counter() - start

        print(
            f"Second request duration: "
            f"{second_duration:.4f} seconds"
        )

        print(
            f"Second audio size: "
            f"{len(audio_2)} bytes"
        )

        if not audio_2:
            raise RuntimeError(
                "Second TTS request returned empty audio."
            )

        if audio_1 != audio_2:
            raise RuntimeError(
                "Cache returned different audio bytes "
                "for the same text and language."
            )

        print()
        print("Audio bytes identical: YES")

        print()
        print("=" * 60)
        print("TTS CACHE INTEGRATION TEST PASSED")
        print("=" * 60)

    finally:
        provider.close()


if __name__ == "__main__":
    main()