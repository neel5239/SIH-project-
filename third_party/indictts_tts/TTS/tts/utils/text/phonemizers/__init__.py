from TTS.tts.utils.text.phonemizers.base import BasePhonemizer


# Phonemizers are only required when a model uses phonemes.
# The AI4Bharat Hindi Indic-TTS checkpoint uses:
#     use_phonemes = false
#
# Therefore we intentionally do not import the Japanese MeCab
# phonemizer during package initialization.

DEF_LANG_TO_PHONEMIZER = {
    "en": "espeak",
    "de": "espeak",
    "fr": "espeak",
    "es": "espeak",
    "it": "espeak",
    "pt": "espeak",
    "ru": "espeak",
    "zh": "zh",
}


def get_phonemizer_by_name(name: str, language: str | None = None):
    if name == "espeak":
        from TTS.tts.utils.text.phonemizers.espeak_wrapper import ESpeak
        return ESpeak(language=language)

    if name == "gruut":
        from TTS.tts.utils.text.phonemizers.gruut_wrapper import Gruut
        return Gruut(language=language)

    if name == "zh":
        from TTS.tts.utils.text.phonemizers.zh_cn_phonemizer import ZhCmnPinyin
        return ZhCmnPinyin()

    raise ValueError(f"Phonemizer '{name}' is not available.")


__all__ = [
    "BasePhonemizer",
    "DEF_LANG_TO_PHONEMIZER",
    "get_phonemizer_by_name",
]