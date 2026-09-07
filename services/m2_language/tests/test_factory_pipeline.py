from pathlib import Path

from services.m2_language.providers.factory import create_language_provider
from services.m2_language.services.pipeline import M2LanguagePipeline


AUDIO_PATH = Path(
    "services/m2_language/tests/audio/sarvam_pipeline_test.wav"
)


def main():
    print("M2 REAL FACTORY PIPELINE TEST")

    assert AUDIO_PATH.exists(), f"Audio not found: {AUDIO_PATH}"

    provider = create_language_provider()

    print(f"Provider wrapper: {type(provider).__name__}")
    print(f"Primary: {type(provider.primary).__name__}")
    print(f"Fallback: {type(provider.fallback).__name__}")

    pipeline = M2LanguagePipeline(
        provider=provider,
    )

    result = pipeline.process_inbound(
        audio_path=str(AUDIO_PATH),
        source_language="hi-IN",
        target_language="en-IN",
    )

    print("\nInbound result:")
    print(f"Transcript: {result.transcript}")
    print(f"English: {result.translated_text}")
    print(f"Provider: {result.provider}")
    print(f"Model: {result.model}")
    print(f"Mode: {result.mode}")
    print(f"Confidence: {result.confidence}")
    print(f"Negation: {result.negation_hint}")

    assert result.translated_text.strip()
    assert result.provider == "sarvam"
    assert result.mode == "online"

    print("\nREAL FACTORY PIPELINE TEST PASSED")

    pipeline.close()


if __name__ == "__main__":
    main()