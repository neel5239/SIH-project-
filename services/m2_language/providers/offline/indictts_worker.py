import base64
import io
import json
import sys
import traceback
import wave
from pathlib import Path

import numpy as np
import torch


# ======================================================================
# PROJECT PATHS
# ======================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

INDICTTS_ROOT = PROJECT_ROOT / "third_party" / "indictts_tts"
COMPAT_TRAINER = INDICTTS_ROOT / "compat_trainer"

sys.path.insert(0, str(INDICTTS_ROOT))
sys.path.insert(0, str(COMPAT_TRAINER))


# ======================================================================
# COMPATIBILITY PATCHES
# ======================================================================

# These must be installed before importing TTS.
import compat_coqpit
import compat_librosa

compat_coqpit.install()
compat_librosa.install()


# ======================================================================
# TTS IMPORTS
# ======================================================================

from TTS.config import load_config
from TTS.tts.models.forward_tts import ForwardTTS
from TTS.vocoder.models import setup_model as setup_vocoder_model


# ======================================================================
# MODEL PATHS
# ======================================================================

FASTPITCH_DIR = (
    PROJECT_ROOT
    / "services"
    / "m2_language"
    / "providers"
    / "offline"
    / "tts_models"
    / "hi"
    / "fastpitch"
)

HIFIGAN_DIR = (
    PROJECT_ROOT
    / "services"
    / "m2_language"
    / "providers"
    / "offline"
    / "tts_models"
    / "hi"
    / "hifigan"
)

FASTPITCH_MODEL = FASTPITCH_DIR / "best_model.pth"
FASTPITCH_CONFIG = FASTPITCH_DIR / "config.json"
SPEAKERS_FILE = FASTPITCH_DIR / "speakers.pth"

HIFIGAN_MODEL = HIFIGAN_DIR / "best_model.pth"
HIFIGAN_CONFIG = HIFIGAN_DIR / "config.json"


# ======================================================================
# GLOBAL MODELS
# ======================================================================

fastpitch_model = None
hifigan_model = None
vocoder_ap = None
sample_rate = 22050


# ======================================================================
# HELPERS
# ======================================================================

def send_response(data: dict) -> None:
    """
    Send exactly one JSON response to stdout.
    """
    print(
        json.dumps(data, ensure_ascii=False),
        flush=True,
    )


def normalize_tts_text(text: str) -> str:
    """
    Normalize punctuation/whitespace for TTS only.

    This does NOT modify the original clinical text.
    """

    text = text.replace("।", ".")
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    while "  " in text:
        text = text.replace("  ", " ")

    return text.strip()


def check_model_files() -> None:
    required_files = [
        FASTPITCH_MODEL,
        FASTPITCH_CONFIG,
        SPEAKERS_FILE,
        HIFIGAN_MODEL,
        HIFIGAN_CONFIG,
    ]

    for path in required_files:
        if not path.exists():
            raise FileNotFoundError(
                f"Required Indic-TTS file not found: {path}"
            )


# ======================================================================
# FASTPITCH CHECKPOINT
# ======================================================================

def load_fastpitch_weights(model, checkpoint_path):
    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )

    if not isinstance(checkpoint, dict):
        raise RuntimeError(
            "FastPitch checkpoint is not a dictionary."
        )

    if "model" not in checkpoint:
        raise RuntimeError(
            "FastPitch checkpoint does not contain a 'model' state."
        )

    state_dict = checkpoint["model"]

    result = model.load_state_dict(
        state_dict,
        strict=False,
    )

    if result.missing_keys:
        raise RuntimeError(
            "FastPitch checkpoint has missing keys: "
            + ", ".join(result.missing_keys[:20])
        )

    if result.unexpected_keys:
        raise RuntimeError(
            "FastPitch checkpoint has unexpected keys: "
            + ", ".join(result.unexpected_keys[:20])
        )


# ======================================================================
# MODEL LOADING
# ======================================================================

def load_models() -> None:
    global fastpitch_model
    global hifigan_model
    global vocoder_ap
    global sample_rate

    check_model_files()

    # ------------------------------------------------------------------
    # FastPitch configuration
    # ------------------------------------------------------------------

    fastpitch_config = load_config(
        str(FASTPITCH_CONFIG)
    )

    # Fix AI4Bharat's relative speaker path.
    fastpitch_config.speakers_file = str(
        SPEAKERS_FILE
    )

    if hasattr(fastpitch_config, "model_args"):
        fastpitch_config.model_args.speakers_file = str(
            SPEAKERS_FILE
        )

    sample_rate = int(
        fastpitch_config.audio.sample_rate
    )

    # ------------------------------------------------------------------
    # Create FastPitch
    # ------------------------------------------------------------------

    fastpitch_model = ForwardTTS.init_from_config(
        fastpitch_config,
    )

    # ------------------------------------------------------------------
    # Load FastPitch checkpoint
    # ------------------------------------------------------------------

    load_fastpitch_weights(
        fastpitch_model,
        FASTPITCH_MODEL,
    )

    # ------------------------------------------------------------------
    # HiFi-GAN configuration
    # ------------------------------------------------------------------

    hifigan_config = load_config(
        str(HIFIGAN_CONFIG)
    )

    sample_rate = int(
        hifigan_config.audio.sample_rate
    )

    # ------------------------------------------------------------------
    # Create HiFi-GAN
    # ------------------------------------------------------------------

    hifigan_model = setup_vocoder_model(
        hifigan_config
    )

    # ------------------------------------------------------------------
    # Load HiFi-GAN checkpoint
    # ------------------------------------------------------------------

    hifigan_model.load_checkpoint(
        hifigan_config,
        str(HIFIGAN_MODEL),
        eval=True,
    )

    vocoder_ap = hifigan_model.ap


# ======================================================================
# MEL EXTRACTION
# ======================================================================

def extract_mel(outputs):
    """
    Locate the mel spectrogram in FastPitch inference output.
    """

    if isinstance(outputs, dict):

        candidates = [
            "mel_postnet_spec",
            "model_outputs",
            "mel",
            "outputs",
        ]

        for key in candidates:

            if key in outputs:

                value = outputs[key]

                if torch.is_tensor(value):
                    return value

    elif torch.is_tensor(outputs):

        return outputs

    elif isinstance(outputs, (list, tuple)):

        for value in outputs:

            if torch.is_tensor(value):
                return value

    raise RuntimeError(
        "Could not locate mel spectrogram in "
        "FastPitch inference output."
    )


# ======================================================================
# MEL PREPARATION
# ======================================================================

def prepare_mel_for_vocoder(mel):
    """
    Convert FastPitch mel into the exact format expected by
    the already-tested HiFi-GAN pipeline.
    """

    if not torch.is_tensor(mel):

        mel = torch.tensor(
            mel,
            dtype=torch.float32,
        )

    mel = mel.detach().cpu()

    # --------------------------------------------------------------
    # Expected final format:
    #
    # [batch, mel_channels, time]
    # --------------------------------------------------------------

    if mel.ndim == 2:

        # [mel, time]
        if mel.shape[0] == 80:

            mel = mel.unsqueeze(0)

        # [time, mel]
        elif mel.shape[1] == 80:

            mel = mel.transpose(0, 1)
            mel = mel.unsqueeze(0)

        else:

            raise RuntimeError(
                "2D mel does not contain 80 mel channels."
            )

    elif mel.ndim == 3:

        # [B, T, 80] -> [B, 80, T]
        if mel.shape[-1] == 80:

            mel = mel.transpose(1, 2)

        # Already [B, 80, T]
        elif mel.shape[1] == 80:

            pass

        else:

            raise RuntimeError(
                "3D mel does not contain 80 mel channels."
            )

    else:

        raise RuntimeError(
            f"Unexpected mel dimensions: {mel.ndim}"
        )

    # --------------------------------------------------------------
    # The original working inference test performs normalization
    # individually in [time, mel] orientation.
    # --------------------------------------------------------------

    normalized_mels = []

    for batch_index in range(
        mel.shape[0]
    ):

        mel_item = mel[
            batch_index
        ].numpy()

        # [80, T] -> [T, 80]
        mel_item = mel_item.T

        normalized = vocoder_ap.normalize(
            mel_item
        )

        # [T, 80] -> [80, T]
        normalized = normalized.T

        normalized_mels.append(
            normalized
        )

    mel = np.stack(
        normalized_mels,
        axis=0,
    )

    return torch.tensor(
        mel,
        dtype=torch.float32,
    )


# ======================================================================
# FASTPITCH INFERENCE
# ======================================================================

def generate_mel(text: str):
    """
    Convert text into a mel spectrogram.
    """

    tokenizer = fastpitch_model.tokenizer

    if hasattr(
        tokenizer,
        "text_to_ids",
    ):

        text_ids = tokenizer.text_to_ids(
            text
        )

    elif hasattr(
        tokenizer,
        "encode",
    ):

        text_ids = tokenizer.encode(
            text
        )

    else:

        raise RuntimeError(
            "FastPitch tokenizer does not provide "
            "text_to_ids() or encode()."
        )

    if not text_ids:

        raise RuntimeError(
            "Tokenizer returned an empty token sequence."
        )

    text_tensor = torch.LongTensor(
        text_ids
    ).unsqueeze(0)

    with torch.no_grad():

        fastpitch_outputs = (
            fastpitch_model.inference(
                text_tensor,
                aux_input={
                    "d_vectors": None,
                    "speaker_ids": torch.LongTensor([0]),
                },
            )
        )

    return extract_mel(
        fastpitch_outputs
    )


# ======================================================================
# HIFIGAN INFERENCE
# ======================================================================

def generate_waveform(mel):
    """
    Convert mel spectrogram into waveform.
    """

    vocoder_input = (
        prepare_mel_for_vocoder(mel)
    )

    with torch.no_grad():

        waveform = (
            hifigan_model.inference(
                vocoder_input
            )
        )

    if torch.is_tensor(waveform):

        waveform = (
            waveform
            .detach()
            .cpu()
            .numpy()
        )

    waveform = np.asarray(
        waveform
    )

    waveform = np.squeeze(
        waveform
    )

    if waveform.ndim != 1:

        raise RuntimeError(
            f"Expected mono waveform, "
            f"got shape {waveform.shape}"
        )

    waveform = np.nan_to_num(
        waveform,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    max_abs = np.max(
        np.abs(waveform)
    )

    if max_abs > 1.0:

        waveform = (
            waveform / max_abs
        )

    waveform = np.clip(
        waveform,
        -1.0,
        1.0,
    )

    return waveform


# ======================================================================
# WAV ENCODING
# ======================================================================

def waveform_to_wav_bytes(
    waveform,
    rate,
) -> bytes:
    """
    Convert waveform into mono 16-bit PCM WAV bytes.
    """

    pcm = (
        waveform * 32767.0
    ).astype(
        np.int16
    )

    buffer = io.BytesIO()

    with wave.open(
        buffer,
        "wb",
    ) as wav_file:

        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)

        wav_file.writeframes(
            pcm.tobytes()
        )

    return buffer.getvalue()


# ======================================================================
# SYNTHESIS
# ======================================================================

def synthesize(
    text: str,
    language: str,
) -> dict:

    if language not in {
        "hi",
        "hi-IN",
    }:

        raise ValueError(
            f"Unsupported Indic-TTS language: "
            f"{language}. "
            "Currently validated: hi / hi-IN."
        )

    if not text or not text.strip():

        raise ValueError(
            "TTS text cannot be empty."
        )

    # Only normalize a local copy used for synthesis.
    normalized_text = (
        normalize_tts_text(text)
    )

    print(
        "Indic-TTS: generating mel...",
        file=sys.stderr,
        flush=True,
    )

    mel = generate_mel(
        normalized_text
    )

    print(
        f"Indic-TTS: mel shape="
        f"{tuple(mel.shape)}",
        file=sys.stderr,
        flush=True,
    )

    print(
        "Indic-TTS: generating waveform...",
        file=sys.stderr,
        flush=True,
    )

    waveform = generate_waveform(
        mel
    )

    wav_bytes = (
        waveform_to_wav_bytes(
            waveform,
            sample_rate,
        )
    )

    audio_base64 = (
        base64.b64encode(
            wav_bytes
        ).decode("ascii")
    )

    duration = (
        len(waveform)
        / sample_rate
    )

    return {
        "success": True,
        "audio_base64": audio_base64,
        "sample_rate": sample_rate,
        "duration_seconds": round(
            duration,
            3,
        ),
        "language_code": language,
        "provider": "ai4bharat",
        "model": "indic-tts-fastpitch-hifigan",
        "mode": "offline",
    }


# ======================================================================
# MAIN WORKER
# ======================================================================

def main() -> None:

    try:

        print(
            "Indic-TTS worker: loading models...",
            file=sys.stderr,
            flush=True,
        )

        load_models()

        print(
            "Indic-TTS worker: models loaded.",
            file=sys.stderr,
            flush=True,
        )

        for line in sys.stdin:

            line = line.strip()

            if not line:
                continue

            try:

                request = json.loads(
                    line
                )

                text = request.get(
                    "text",
                    "",
                )

                language = request.get(
                    "language",
                    "",
                )

                response = synthesize(
                    text=text,
                    language=language,
                )

                send_response(
                    response
                )

            except Exception as exc:

                send_response(
                    {
                        "success": False,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    }
                )

    except Exception as exc:

        send_response(
            {
                "success": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )

        sys.exit(1)


if __name__ == "__main__":
    main()