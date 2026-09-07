"""
Compatibility patch for legacy Coqui / AI4Bharat Indic-TTS
with modern librosa.

Legacy code calls:

    librosa.filters.mel(sr, n_fft, ...)

Modern librosa requires:

    librosa.filters.mel(sr=..., n_fft=..., ...)
"""

import inspect

import librosa


_original_mel = librosa.filters.mel


def mel_legacy_compatible(*args, **kwargs):
    """
    Accept both the old positional librosa.filters.mel() API
    and the modern keyword-only API.
    """

    if args:

        parameter_names = [
            "sr",
            "n_fft",
            "n_mels",
            "fmin",
            "fmax",
            "htk",
            "norm",
            "dtype",
        ]

        for name, value in zip(parameter_names, args):
            if name in kwargs:
                raise TypeError(
                    f"mel() got multiple values for argument '{name}'"
                )

            kwargs[name] = value

    return _original_mel(**kwargs)


def install():
    librosa.filters.mel = mel_legacy_compatible
    return True


install()