"""
Minimal compatibility layer for the legacy Coqui TTS Trainer package.

The AI4Bharat Indic-TTS inference path imports get_optimizer and
get_scheduler from trainer.trainer_utils, but inference does not
require the historical Trainer implementation.
"""


def get_optimizer(*args, **kwargs):
    raise RuntimeError(
        "get_optimizer() is not available in the Python 3.12 "
        "inference compatibility layer."
    )


def get_scheduler(*args, **kwargs):
    raise RuntimeError(
        "get_scheduler() is not available in the Python 3.12 "
        "inference compatibility layer."
    )