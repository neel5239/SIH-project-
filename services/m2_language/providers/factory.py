import os

from .fallback import FallbackLanguageProvider
from .local import LocalProvider
from .sarvam import SarvamProvider


def create_language_provider() -> FallbackLanguageProvider:
    """
    Create the production M2 language provider.

    Sarvam is the online primary provider.
    AI4Bharat LocalProvider is the offline fallback.

    If Sarvam credentials are unavailable, the system starts
    directly in offline mode.
    """

    local_provider = LocalProvider()

    api_key = os.getenv("SARVAM_API_KEY")

    if not api_key:
        return FallbackLanguageProvider(
            primary=local_provider,
            fallback=local_provider,
        )

    try:
        sarvam_provider = SarvamProvider(
            api_key=api_key,
        )

        return FallbackLanguageProvider(
            primary=sarvam_provider,
            fallback=local_provider,
        )

    except Exception:
        return FallbackLanguageProvider(
            primary=local_provider,
            fallback=local_provider,
        )