import json
import sys
import traceback
import wave
from pathlib import Path

import torch


MODEL_PATH = Path(
    r"C:\Users\Lenovo\.cache\huggingface\hub"
    r"\models--ai4bharat--indic-conformer-600m-multilingual"
    r"\snapshots\e9b71b369c048e2c6b634d4c131061c34e441179"
)


print(
    "Loading IndicConformer configuration...",
    file=sys.stderr,
    flush=True,
)

sys.path.insert(0, str(MODEL_PATH))

from model_onnx import IndicASRConfig, IndicASRModel


print(
    "Loading IndicConformer model...",
    file=sys.stderr,
    flush=True,
)

config = IndicASRConfig(
    ts_folder=str(MODEL_PATH)
)

model = IndicASRModel(config)

print(
    "IndicConformer worker ready.",
    file=sys.stderr,
    flush=True,
)


LANGUAGE_MAP = {
    "as": "as",
    "as-IN": "as",

    "bn": "bn",
    "bn-IN": "bn",

    "brx": "brx",

    "doi": "doi",

    "gu": "gu",
    "gu-IN": "gu",

    "hi": "hi",
    "hi-IN": "hi",

    "kn": "kn",
    "kn-IN": "kn",

    "kok": "kok",

    "ks": "ks",

    "mai": "mai",

    "ml": "ml",
    "ml-IN": "ml",

    "mni": "mni",

    "mr": "mr",
    "mr-IN": "mr",

    "ne": "ne",
    "ne-IN": "ne",

    "or": "or",
    "or-IN": "or",

    "pa": "pa",
    "pa-IN": "pa",

    "sa": "sa",

    "sat": "sat",

    "sd": "sd",

    "ta": "ta",
    "ta-IN": "ta",

    "te": "te",
    "te-IN": "te",

    "ur": "ur",
    "ur-IN": "ur",
}


def map_language(language: str) -> str:
    normalized = language.strip()

    if normalized in LANGUAGE_MAP:
        return LANGUAGE_MAP[normalized]

    raise ValueError(
        f"Unsupported IndicConformer language code: {language}"
    )


def load_wav(audio_path: str) -> tuple[torch.Tensor, int]:
    """
    Load a PCM WAV file without torchaudio or FFmpeg.

    Returns:
        waveform: Tensor with shape [1, samples]
        sample_rate: integer sample rate
    """

    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {path}"
        )

    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        frame_count = wav.getnframes()
        raw_audio = wav.readframes(frame_count)

    if sample_width != 2:
        raise ValueError(
            "IndicConformer worker currently requires "
            "16-bit PCM WAV audio."
        )

    if sample_rate != 16000:
        raise ValueError(
            f"IndicConformer requires 16 kHz audio. "
            f"Received {sample_rate} Hz."
        )

    import numpy as np

    audio = np.frombuffer(
        raw_audio,
        dtype=np.int16,
    ).astype(np.float32)

    # Convert int16 PCM to approximately [-1, 1].
    audio = audio / 32768.0

    if channels > 1:
        audio = audio.reshape(-1, channels)
        audio = audio.mean(axis=1)

    waveform = torch.from_numpy(audio).unsqueeze(0)

    return waveform, sample_rate


def transcribe(
    audio_path: str,
    language: str,
) -> str:

    lang = map_language(language)

    waveform, sample_rate = load_wav(audio_path)

    if sample_rate != 16000:
        raise ValueError(
            f"Expected 16000 Hz audio, got {sample_rate} Hz."
        )

    with torch.no_grad():
        transcription = model(
            waveform,
            lang,
            "ctc",
        )

    return transcription


for line in sys.stdin:
    line = line.strip()

    if not line:
        continue

    try:
        request = json.loads(line)

        audio_path = request["audio_path"]
        language = request["language"]

        transcript = transcribe(
            audio_path,
            language,
        )

        response = {
            "success": True,
            "transcript": transcript,
            "language_code": language,
            "provider": "ai4bharat",
            "model": "indic-conformer-600m-multilingual",
            "mode": "offline",
        }

    except Exception as exc:
        response = {
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    print(
        json.dumps(
            response,
            ensure_ascii=False,
        ),
        flush=True,
    )