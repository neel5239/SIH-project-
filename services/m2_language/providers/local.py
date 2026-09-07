import base64
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .base import LanguageProvider


class LocalProvider(LanguageProvider):
    """
    Offline M2 language provider.

    IndicConformerASR is used for offline speech-to-text.
    IndicTrans2 is used for offline translation.
    AI4Bharat Indic-TTS is used for offline text-to-speech.

    Each model family runs in its own worker environment so that
    dependency requirements do not interfere with each other.
    """

    LANGUAGE_MAP = {
        "en": "eng_Latn",
        "en-IN": "eng_Latn",

        "hi": "hin_Deva",
        "hi-IN": "hin_Deva",

        "bn": "ben_Beng",
        "bn-IN": "ben_Beng",

        "gu": "guj_Gujr",
        "gu-IN": "guj_Gujr",

        "kn": "kan_Knda",
        "kn-IN": "kan_Knda",

        "ml": "mal_Mlym",
        "ml-IN": "mal_Mlym",

        "mr": "mar_Deva",
        "mr-IN": "mar_Deva",

        "ne": "npi_Deva",
        "ne-IN": "npi_Deva",

        "or": "ory_Orya",
        "or-IN": "ory_Orya",

        "pa": "pan_Guru",
        "pa-IN": "pan_Guru",

        "ta": "tam_Taml",
        "ta-IN": "tam_Taml",

        "te": "tel_Telu",
        "te-IN": "tel_Telu",
    }

    CONFORMER_LANGUAGE_MAP = {
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

    def __init__(self, worker_python: str | None = None):
        project_root = Path(__file__).resolve().parents[3]

        # --------------------------------------------------------------
        # IndicTrans2 environment
        # --------------------------------------------------------------

        default_python = (
            project_root
            / ".venv_indictrans"
            / "Scripts"
            / "python.exe"
        )

        self.worker_python = Path(
            worker_python
            or os.getenv("MEDISAARTHI_INDIC_PYTHON")
            or default_python
        )

        # --------------------------------------------------------------
        # Offline worker directory
        # --------------------------------------------------------------

        offline_dir = (
            project_root
            / "services"
            / "m2_language"
            / "providers"
            / "offline"
        )

        self.indictrans_worker = (
            offline_dir / "indictrans_worker.py"
        )

        self.indicconformer_worker = (
            offline_dir / "indicconformer_worker.py"
        )

        self.indictts_worker = (
            offline_dir / "indictts_worker.py"
        )

        # --------------------------------------------------------------
        # IndicConformer uses the main MediSaarthi environment.
        # --------------------------------------------------------------

        self.main_python = Path(
            os.sys.executable
        )

        # --------------------------------------------------------------
        # Indic-TTS uses its dedicated environment.
        # --------------------------------------------------------------

        default_tts_python = (
            project_root
            / ".venv_indictts"
            / "Scripts"
            / "python.exe"
        )

        self.tts_python = Path(
            os.getenv("MEDISAARTHI_INDIC_TTS_PYTHON")
            or default_tts_python
        )

    # ==================================================================
    # STT
    # ==================================================================

    def speech_to_text(
        self,
        audio_path: str,
        source_language: str | None = None,
    ) -> dict[str, Any]:

        if not source_language:
            raise ValueError(
                "source_language is required for offline STT."
            )

        audio = Path(audio_path)

        if not audio.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio}"
            )

        if not self.indicconformer_worker.exists():
            raise FileNotFoundError(
                "IndicConformer worker not found: "
                f"{self.indicconformer_worker}"
            )

        language_code = self._map_conformer_language(
            source_language
        )

        request = {
            "audio_path": str(audio),
            "language": language_code,
        }

        request_json = json.dumps(
            request,
            ensure_ascii=False,
        )

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            result = subprocess.run(
                [
                    str(self.main_python),
                    str(self.indicconformer_worker),
                ],
                input=request_json + "\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=180,
            )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "IndicConformer STT timed out."
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                "IndicConformer worker failed.\n"
                f"Return code: {result.returncode}\n"
                f"stderr:\n{result.stderr}"
            )

        response = self._parse_worker_response(
            result.stdout,
            "IndicConformer",
        )

        if not response.get("success"):
            raise RuntimeError(
                response.get(
                    "error",
                    "IndicConformer STT failed.",
                )
            )

        return {
            "transcript": response["transcript"],
            "language_code": source_language,
            "provider": "ai4bharat",
            "model": "indic-conformer-600m-multilingual",
            "mode": "offline",
            "confidence": None,
        }

    # ==================================================================
    # TRANSLATION
    # ==================================================================

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> dict[str, Any]:

        if not text.strip():
            raise ValueError("Text cannot be empty.")

        source_code = self._map_language(
            source_language
        )

        target_code = self._map_language(
            target_language
        )

        if not self.worker_python.exists():
            raise FileNotFoundError(
                f"IndicTrans2 Python environment not found: "
                f"{self.worker_python}"
            )

        if not self.indictrans_worker.exists():
            raise FileNotFoundError(
                f"IndicTrans2 worker not found: "
                f"{self.indictrans_worker}"
            )

        request = {
            "text": text,
            "source_language": source_code,
            "target_language": target_code,
        }

        request_json = json.dumps(
            request,
            ensure_ascii=False,
        )

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            result = subprocess.run(
                [
                    str(self.worker_python),
                    str(self.indictrans_worker),
                ],
                input=request_json + "\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=180,
            )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "IndicTrans2 translation timed out."
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                "IndicTrans2 worker failed.\n"
                f"Return code: {result.returncode}\n"
                f"stderr:\n{result.stderr}"
            )

        response = self._parse_worker_response(
            result.stdout,
            "IndicTrans2",
        )

        if not response.get("success"):
            raise RuntimeError(
                response.get(
                    "error",
                    "IndicTrans2 translation failed.",
                )
            )
        if source_code == "eng_Latn" and target_code != "eng_Latn":
            model_name = "indictrans2-en-indic-dist-200M"
        elif source_code != "eng_Latn" and target_code == "eng_Latn":
            model_name = "indictrans2-indic-en-dist-200M"
        else:
            model_name = "indictrans2"
        return {
            "translated_text": response["translated_text"],
            "source_language_code": source_language,
            "target_language_code": target_language,
            "provider": "ai4bharat",
            "model": model_name,
            "mode": "offline",
        }

    # ==================================================================
    # TEXT TO SPEECH
    # ==================================================================

    def text_to_speech(
        self,
        text: str,
        language: str,
    ) -> bytes:

        if not text or not text.strip():
            raise ValueError(
                "TTS text cannot be empty."
            )

        if not language or not language.strip():
            raise ValueError(
                "TTS language is required."
            )

        if not self.tts_python.exists():
            raise FileNotFoundError(
                "Indic-TTS Python environment not found: "
                f"{self.tts_python}"
            )

        if not self.indictts_worker.exists():
            raise FileNotFoundError(
                "Indic-TTS worker not found: "
                f"{self.indictts_worker}"
            )

        request = {
            "text": text,
            "language": language,
        }

        request_json = json.dumps(
            request,
            ensure_ascii=False,
        )

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            result = subprocess.run(
                [
                    str(self.tts_python),
                    str(self.indictts_worker),
                ],
                input=request_json + "\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=300,
            )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "Indic-TTS synthesis timed out."
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                "Indic-TTS worker failed.\n"
                f"Return code: {result.returncode}\n"
                f"stderr:\n{result.stderr}"
            )

        response = self._parse_worker_response(
            result.stdout,
            "Indic-TTS",
        )

        if not response.get("success"):
            raise RuntimeError(
                response.get(
                    "error",
                    "Indic-TTS synthesis failed.",
                )
            )

        audio_base64 = response.get(
            "audio_base64"
        )

        if not audio_base64:
            raise RuntimeError(
                "Indic-TTS worker returned no audio."
            )

        try:
            audio = base64.b64decode(
                audio_base64,
                validate=True,
            )

        except Exception as exc:
            raise RuntimeError(
                "Indic-TTS worker returned invalid "
                "base64 audio."
            ) from exc

        if not audio:
            raise RuntimeError(
                "Indic-TTS worker returned empty audio."
            )

        # Basic WAV validation.
        if not audio.startswith(b"RIFF") or b"WAVE" not in audio[:16]:
            raise RuntimeError(
                "Indic-TTS worker returned audio that "
                "does not appear to be a WAV file."
            )

        return audio

    # ==================================================================
    # LANGUAGE MAPPING
    # ==================================================================

    @classmethod
    def _map_language(
        cls,
        language: str,
    ) -> str:

        normalized = language.strip()

        if normalized in cls.LANGUAGE_MAP:
            return cls.LANGUAGE_MAP[normalized]

        if "_" in normalized:
            return normalized

        raise ValueError(
            f"Unsupported offline translation language code: "
            f"{language}"
        )

    @classmethod
    def _map_conformer_language(
        cls,
        language: str,
    ) -> str:

        normalized = language.strip()

        if normalized in cls.CONFORMER_LANGUAGE_MAP:
            return cls.CONFORMER_LANGUAGE_MAP[normalized]

        raise ValueError(
            f"Unsupported offline STT language code: "
            f"{language}"
        )

    # ==================================================================
    # WORKER RESPONSE PARSER
    # ==================================================================

    @staticmethod
    def _parse_worker_response(
        stdout: str,
        worker_name: str,
    ) -> dict[str, Any]:

        response_line = ""

        for line in stdout.splitlines():

            line = line.strip()

            if line.startswith("{") and line.endswith("}"):
                response_line = line

        if not response_line:
            raise RuntimeError(
                f"{worker_name} worker returned no JSON response.\n"
                f"stdout:\n{stdout}"
            )

        try:
            return json.loads(
                response_line
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Invalid JSON returned by "
                f"{worker_name} worker.\n"
                f"Response: {response_line}"
            ) from exc

    # ==================================================================
    # CLOSE
    # ==================================================================

    def close(self) -> None:
        """
        Compatibility method.

        The current implementation uses short-lived worker
        processes, so there is no persistent process to close.
        """
        pass