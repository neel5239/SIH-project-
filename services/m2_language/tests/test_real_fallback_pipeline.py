from pathlib import Path

from services.m2_language.providers.local import LocalProvider
from services.m2_language.providers.sarvam import SarvamProvider
from services.m2_language.providers.fallback import FallbackLanguageProvider
from services.m2_language.services.pipeline import M2LanguagePipeline


AUDIO_PATH = Path(
    "services/m2_language/tests/audio/sarvam_pipeline_test.wav"
)


class FailingSarvamProvider(SarvamProvider):
    """
    Real Sarvam provider whose STT and translation are deliberately
    forced to fail.

    This simulates an online service outage while keeping the
    real LocalProvider as the offline fallback.
    """

    def speech_to_text(
        self,
        audio_path: str,
        source_language: str | None = None,
    ):
        raise RuntimeError(
            "Simulated Sarvam STT outage for fallback test."
        )

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ):
        raise RuntimeError(
            "Simulated Sarvam translation outage for fallback test."
        )


def main():
    print("M2 REAL ONLINE -> OFFLINE FALLBACK PIPELINE TEST")

    assert AUDIO_PATH.exists(), (
        f"Audio file not found: {AUDIO_PATH}"
    )

    print("\nCreating real providers...")

    primary = FailingSarvamProvider()
    fallback = LocalProvider()

    provider = FallbackLanguageProvider(
        primary=primary,
        fallback=fallback,
    )

    print(f"Wrapper: {type(provider).__name__}")
    print(f"Primary: {type(provider.primary).__name__}")
    print(f"Fallback: {type(provider.fallback).__name__}")

    pipeline = M2LanguagePipeline(
        provider=provider,
    )

    print("\nRunning inbound pipeline...")
    print("Sarvam STT will intentionally fail.")
    print("AI4Bharat LocalProvider should take over.\n")

    result = pipeline.process_inbound(
        audio_path=str(AUDIO_PATH),
        source_language="hi-IN",
        target_language="en-IN",
    )

    print("Inbound result:")
    print(f"Transcript: {result.transcript}")
    print(f"English: {result.translated_text}")
    print(f"Provider: {result.provider}")
    print(f"Model: {result.model}")
    print(f"Mode: {result.mode}")
    print(f"Confidence: {result.confidence}")
    print(f"Negation: {result.negation_hint}")

    assert result.translated_text.strip()

    assert result.provider == "ai4bharat"
    assert result.mode == "offline"

    assert provider.last_mode == "offline"
    assert provider.last_error is not None
    assert (
        "Simulated Sarvam STT outage" in provider.last_error
        or
        "Simulated Sarvam translation outage" in provider.last_error
    )

    print("\nREAL ONLINE -> OFFLINE FALLBACK TEST PASSED")

    pipeline.close()


if __name__ == "__main__":
    main()