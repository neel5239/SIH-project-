from dataclasses import dataclass
from typing import Any, Callable
import os
import tempfile

from services.m2_language.providers.base import LanguageProvider
from services.m2_language.services.language_service import CodeMixNormalizer
from services.m2_language.services.masking import ProtectedTermMasker
from services.m2_language.services.negation import NegationDetector
from services.m2_language.services.tts_cache import TTSCache
from services.m2_language.utils.audio import AudioPreprocessor


@dataclass
class InboundResult:
    """
    M2 inbound result passed to M3.

    This object contains the normalized English text plus
    language-engine provenance and a lightweight negation hint.
    """

    transcript: str
    normalized_transcript: str
    translated_text: str
    source_language: str
    target_language: str
    provider: str
    model: str | None
    mode: str
    confidence: float | None
    negation_hint: bool
    negation_terms: list[str]
    normalization_changes: list[str]


@dataclass
class OutboundResult:
    """
    M2 outbound result returned after translating and synthesizing
    an English question for the patient.
    """

    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    audio: bytes
    provider: str
    model: str | None
    mode: str
    cache_hit: bool


class M2LanguagePipeline:
    """
    Orchestrates the M2 language pipeline.

    Inbound:
        audio
        -> VAD
        -> noise suppression
        -> STT
        -> code-mix normalization
        -> negation detection
        -> protected-term masking
        -> translation to English
        -> unmask
        -> M3-ready result

    Outbound:
        English question
        -> protected-term masking
        -> translation to patient language
        -> unmask
        -> TTS cache
        -> TTS
        -> audio

    The pipeline does not make clinical decisions.
    """

    def __init__(
        self,
        provider: LanguageProvider,
        normalizer: CodeMixNormalizer | None = None,
        masker: ProtectedTermMasker | None = None,
        negation_detector: NegationDetector | None = None,
        tts_cache: TTSCache | None = None,
        audio_preprocessor: AudioPreprocessor | None = None,
    ):
        self.provider = provider

        self.normalizer = (
            normalizer
            or CodeMixNormalizer()
        )

        self.masker = (
            masker
            or ProtectedTermMasker()
        )

        self.negation_detector = (
            negation_detector
            or NegationDetector()
        )

        self.tts_cache = (
            tts_cache
            or TTSCache()
        )

        self.audio_preprocessor = (
            audio_preprocessor
            or AudioPreprocessor()
        )

    # ==================================================================
    # INBOUND
    # ==================================================================

    def process_inbound(
        self,
        audio_path: str,
        source_language: str,
        target_language: str = "en-IN",
    ) -> InboundResult:
        """
        Process patient speech and return an M3-ready result.

        Inbound audio is first normalized through the M2 audio
        preprocessing layer:

            audio -> VAD -> noise suppression -> STT
        """

        if not audio_path:
            raise ValueError(
                "audio_path is required."
            )

        if not source_language:
            raise ValueError(
                "source_language is required."
            )

        if not target_language:
            raise ValueError(
                "target_language is required."
            )

        preprocessed_path: str | None = None

        try:
            # ----------------------------------------------------------
            # 1. Audio preprocessing
            # ----------------------------------------------------------
            #
            # The preprocessor creates a temporary 16 kHz mono WAV
            # containing the speech-active region after noise
            # suppression.
            #
            # We do not overwrite the original input audio.
            # ----------------------------------------------------------

            input_suffix = os.path.splitext(
                audio_path
            )[1].lower()

            if input_suffix != ".wav":
                raise ValueError(
                    "M2 audio preprocessing currently requires "
                    "a WAV input file."
                )

            temp_file = tempfile.NamedTemporaryFile(
                prefix="m2_preprocessed_",
                suffix=".wav",
                delete=False,
            )

            preprocessed_path = temp_file.name
            temp_file.close()

            preprocessing = self.audio_preprocessor.process(
                input_path=audio_path,
                output_path=preprocessed_path,
            )

            if not preprocessing.speech_detected:
                raise RuntimeError(
                    "No speech activity detected in inbound audio."
                )

            # ----------------------------------------------------------
            # 2. Speech-to-text
            # ----------------------------------------------------------

            stt_result = self.provider.speech_to_text(
                audio_path=preprocessed_path,
                source_language=source_language,
            )

            transcript = stt_result.get(
                "transcript",
                "",
            )

            if not transcript or not transcript.strip():
                raise RuntimeError(
                    "Speech-to-text returned an empty transcript."
                )

            # ----------------------------------------------------------
            # 3. Code-mix normalization
            # ----------------------------------------------------------

            normalization = self.normalizer.normalize(
                transcript
            )

            normalized_text = normalization.normalized_text

            # ----------------------------------------------------------
            # 4. Negation detection
            #
            # This intentionally happens BEFORE translation.
            # ----------------------------------------------------------

            negation = self.negation_detector.detect(
                normalized_text
            )

            # ----------------------------------------------------------
            # 5. Protected-term masking
            # ----------------------------------------------------------

            masking = self.masker.mask(
                normalized_text
            )

            # ----------------------------------------------------------
            # 6. Translation to English
            # ----------------------------------------------------------

            translation = self.provider.translate(
                text=masking.masked_text,
                source_language=source_language,
                target_language=target_language,
            )

            translated_text = translation.get(
                "translated_text",
                "",
            )

            if not translated_text or not translated_text.strip():
                raise RuntimeError(
                    "Translation returned empty text."
                )

            # ----------------------------------------------------------
            # 7. Restore protected terms
            # ----------------------------------------------------------

            translated_text = self.masker.unmask(
                translated_text,
                masking.protected_terms,
            )

            # ----------------------------------------------------------
            # 8. Return M3-ready result
            # ----------------------------------------------------------

            return InboundResult(
                transcript=transcript,
                normalized_transcript=normalized_text,
                translated_text=translated_text,
                source_language=source_language,
                target_language=target_language,
                provider=translation.get(
                    "provider",
                    stt_result.get(
                        "provider",
                        "unknown",
                    ),
                ),
                model=translation.get(
                    "model"
                ),
                mode=translation.get(
                    "mode",
                    stt_result.get(
                        "mode",
                        "unknown",
                    ),
                ),
                confidence=stt_result.get(
                    "confidence"
                ),
                negation_hint=negation.has_negation,
                negation_terms=negation.matched_terms,
                normalization_changes=normalization.changes,
            )

        finally:
            # ----------------------------------------------------------
            # Always remove the temporary preprocessed audio.
            # ----------------------------------------------------------

            if preprocessed_path is not None:
                try:
                    if os.path.exists(preprocessed_path):
                        os.remove(preprocessed_path)
                except OSError:
                    pass

    # ==================================================================
    # OUTBOUND
    # ==================================================================

    def process_outbound(
        self,
        text: str,
        target_language: str,
        source_language: str = "en-IN",
    ) -> OutboundResult:
        """
        Translate an English question into the patient's language
        and synthesize it using the TTS cache.
        """

        if not text or not text.strip():
            raise ValueError(
                "Outbound text cannot be empty."
            )

        if not target_language:
            raise ValueError(
                "target_language is required."
            )

        # --------------------------------------------------------------
        # 1. Protect important medical terms
        # --------------------------------------------------------------

        masking = self.masker.mask(
            text
        )

        # --------------------------------------------------------------
        # 2. Translate English -> patient language
        # --------------------------------------------------------------

        translation = self.provider.translate(
            text=masking.masked_text,
            source_language=source_language,
            target_language=target_language,
        )

        translated_text = translation.get(
            "translated_text",
            "",
        )

        if not translated_text or not translated_text.strip():
            raise RuntimeError(
                "Outbound translation returned empty text."
            )

        # --------------------------------------------------------------
        # 3. Restore protected terms
        # --------------------------------------------------------------

        translated_text = self.masker.unmask(
            translated_text,
            masking.protected_terms,
        )

        # --------------------------------------------------------------
        # 4. TTS cache
        # --------------------------------------------------------------

        cache_path = self.tts_cache._cache_path(
            translated_text,
            target_language,
        )

        cache_hit = cache_path.exists()

        audio = self.tts_cache.get_or_create(
            translated_text,
            target_language,
            self.provider.text_to_speech,
        )

        # --------------------------------------------------------------
        # 5. Return M2 outbound result
        # --------------------------------------------------------------

        return OutboundResult(
            source_text=text,
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            audio=audio,
            provider=translation.get(
                "provider",
                "unknown",
            ),
            model=translation.get(
                "model"
            ),
            mode=translation.get(
                "mode",
                "unknown",
            ),
            cache_hit=cache_hit,
        )

    # ==================================================================
    # SIMPLE HELPERS
    # ==================================================================

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> dict[str, Any]:
        """
        Direct translation helper.

        Useful when another M2 component needs translation without
        the complete inbound/outbound pipeline.
        """

        if not text or not text.strip():
            raise ValueError(
                "Translation text cannot be empty."
            )

        masking = self.masker.mask(text)

        result = self.provider.translate(
            text=masking.masked_text,
            source_language=source_language,
            target_language=target_language,
        )

        translated_text = result.get(
            "translated_text",
            "",
        )

        if not translated_text:
            raise RuntimeError(
                "Translation returned empty text."
            )

        result["translated_text"] = self.masker.unmask(
            translated_text,
            masking.protected_terms,
        )

        return result

    def close(self) -> None:
        """
        Close the underlying provider if it exposes close().
        """

        close_method: Callable[[], None] | None = getattr(
            self.provider,
            "close",
            None,
        )

        if close_method is not None:
            close_method()