from dataclasses import dataclass
from pathlib import Path
import wave

import torch
import torchaudio


@dataclass
class AudioPreprocessResult:
    input_path: str
    output_path: str
    sample_rate: int
    channels: int
    duration_seconds: float
    speech_detected: bool
    vad_applied: bool
    noise_suppression_applied: bool


class AudioPreprocessor:
    TARGET_SAMPLE_RATE = 16000

    def __init__(
        self,
        silence_threshold: float = 0.01,
        frame_duration_ms: int = 30,
    ):
        if silence_threshold <= 0:
            raise ValueError("silence_threshold must be positive.")

        if frame_duration_ms not in (10, 20, 30):
            raise ValueError(
                "frame_duration_ms must be 10, 20, or 30."
            )

        self.silence_threshold = silence_threshold
        self.frame_duration_ms = frame_duration_ms

    def load_audio(
        self,
        audio_path: str,
    ) -> tuple[torch.Tensor, int]:
        """
        Load WAV audio using Python's standard wave module.

        This intentionally avoids torchaudio.load() because the
        current torchaudio installation routes audio decoding
        through TorchCodec.
        """
        if not audio_path:
            raise ValueError("audio_path is required.")

        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Audio file does not exist: {audio_path}"
            )

        if path.suffix.lower() != ".wav":
            raise ValueError(
                "AudioPreprocessor currently expects a WAV input file."
            )

        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            frame_count = wav_file.getnframes()
            raw_audio = wav_file.readframes(frame_count)

        if channels <= 0:
            raise ValueError("Invalid channel count.")

        if sample_rate <= 0:
            raise ValueError("Invalid sample rate.")

        if frame_count <= 0 or not raw_audio:
            raise ValueError("Audio file contains no samples.")

        if sample_width == 1:
            audio = torch.tensor(
                list(raw_audio),
                dtype=torch.float32,
            )
            audio = (audio - 128.0) / 128.0

        elif sample_width == 2:
            audio = torch.frombuffer(
                bytearray(raw_audio),
                dtype=torch.int16,
            ).clone().float()
            audio = audio / 32768.0

        elif sample_width == 4:
            audio = torch.frombuffer(
                bytearray(raw_audio),
                dtype=torch.int32,
            ).clone().float()
            audio = audio / 2147483648.0

        else:
            raise ValueError(
                f"Unsupported WAV sample width: {sample_width} bytes."
            )

        audio = audio.reshape(-1, channels)

        waveform = audio.transpose(0, 1).contiguous()

        return waveform, sample_rate

    def convert_to_mono(
        self,
        waveform: torch.Tensor,
    ) -> torch.Tensor:
        """Convert multi-channel audio to mono."""
        if waveform.ndim != 2:
            raise ValueError(
                "Expected waveform shape [channels, samples]."
            )

        if waveform.shape[0] == 1:
            return waveform

        return waveform.mean(dim=0, keepdim=True)

    def resample(
        self,
        waveform: torch.Tensor,
        sample_rate: int,
    ) -> tuple[torch.Tensor, int]:
        """Resample audio to the M2 target rate of 16 kHz."""
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive.")

        if sample_rate == self.TARGET_SAMPLE_RATE:
            return waveform, sample_rate

        resampler = torchaudio.transforms.Resample(
            orig_freq=sample_rate,
            new_freq=self.TARGET_SAMPLE_RATE,
        )

        waveform = resampler(waveform)

        return waveform, self.TARGET_SAMPLE_RATE

    def _frame_rms(
        self,
        waveform: torch.Tensor,
    ) -> torch.Tensor:
        """Calculate RMS energy for fixed-size frames."""
        samples_per_frame = int(
            self.TARGET_SAMPLE_RATE
            * self.frame_duration_ms
            / 1000
        )

        if samples_per_frame <= 0:
            raise RuntimeError("Invalid VAD frame size.")

        total_samples = waveform.shape[1]

        if total_samples < samples_per_frame:
            waveform = torch.nn.functional.pad(
                waveform,
                (0, samples_per_frame - total_samples),
            )

        frame_count = waveform.shape[1] // samples_per_frame

        waveform = waveform[
            :,
            : frame_count * samples_per_frame,
        ]

        frames = waveform.reshape(
            1,
            frame_count,
            samples_per_frame,
        )

        rms = torch.sqrt(
            torch.mean(frames ** 2, dim=2)
            + 1e-10
        )

        return rms.squeeze(0)

    def apply_vad(
        self,
        waveform: torch.Tensor,
    ) -> tuple[torch.Tensor, bool]:
        """
        Energy-based voice activity detection.

        Keeps the region between the first and last active
        frames so pauses inside speech are preserved.
        """
        rms = self._frame_rms(waveform)

        active = rms >= self.silence_threshold

        if not torch.any(active):
            return waveform, False

        active_indices = torch.where(active)[0]

        samples_per_frame = int(
            self.TARGET_SAMPLE_RATE
            * self.frame_duration_ms
            / 1000
        )

        start_frame = int(active_indices[0])
        end_frame = int(active_indices[-1]) + 1

        start_sample = start_frame * samples_per_frame
        end_sample = min(
            end_frame * samples_per_frame,
            waveform.shape[1],
        )

        trimmed = waveform[:, start_sample:end_sample]

        return trimmed, True

    def apply_noise_suppression(
        self,
        waveform: torch.Tensor,
    ) -> torch.Tensor:
        """
        Lightweight spectral noise suppression using
        PyTorch STFT/ISTFT.
        """
        if waveform.numel() == 0:
            return waveform

        mono = waveform.squeeze(0)

        n_fft = 512
        hop_length = 128

        if mono.numel() < n_fft:
            return waveform

        window = torch.hann_window(
            n_fft,
            device=mono.device,
            dtype=mono.dtype,
        )

        spectrum = torch.stft(
            mono,
            n_fft=n_fft,
            hop_length=hop_length,
            window=window,
            return_complex=True,
        )

        magnitude = torch.abs(spectrum)

        frame_energy = magnitude.mean(dim=0)

        noise_frame_count = max(
            1,
            int(frame_energy.numel() * 0.10),
        )

        quiet_indices = torch.argsort(frame_energy)[
            :noise_frame_count
        ]

        noise_profile = magnitude[
            :,
            quiet_indices,
        ].mean(dim=1, keepdim=True)

        threshold = noise_profile * 1.5

        cleaned_magnitude = torch.where(
            magnitude >= threshold,
            magnitude,
            magnitude * 0.15,
        )

        phase = torch.angle(spectrum)

        cleaned_spectrum = (
            cleaned_magnitude
            * torch.exp(1j * phase)
        )

        cleaned = torch.istft(
            cleaned_spectrum,
            n_fft=n_fft,
            hop_length=hop_length,
            window=window,
            length=mono.numel(),
        )

        return cleaned.unsqueeze(0)

    def save_wav(
        self,
        waveform: torch.Tensor,
        output_path: str,
        sample_rate: int,
    ) -> None:
        """
        Save mono floating-point waveform as 16-bit PCM WAV
        using Python's standard wave module.

        This intentionally avoids torchaudio.save() and
        therefore avoids TorchCodec.
        """
        if waveform.ndim != 2:
            raise ValueError(
                "Expected waveform shape [channels, samples]."
            )

        if waveform.shape[0] != 1:
            raise ValueError(
                "save_wav expects mono audio."
            )

        waveform = waveform.detach().cpu().clamp(-1.0, 1.0)

        pcm = (
            waveform.squeeze(0)
            * 32767.0
        ).to(torch.int16)

        raw_audio = pcm.numpy().tobytes()

        output_file = Path(output_path)

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with wave.open(str(output_file), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(raw_audio)

    def process(
        self,
        input_path: str,
        output_path: str | None = None,
    ) -> AudioPreprocessResult:
        """Run the complete M2 audio preprocessing pipeline."""
        waveform, sample_rate = self.load_audio(input_path)

        waveform = self.convert_to_mono(waveform)

        waveform, sample_rate = self.resample(
            waveform,
            sample_rate,
        )

        waveform, speech_detected = self.apply_vad(
            waveform,
        )

        if not speech_detected:
            raise RuntimeError(
                "No speech activity detected in the audio."
            )

        waveform = self.apply_noise_suppression(
            waveform,
        )

        if output_path is None:
            input_file = Path(input_path)
            output_path = str(
                input_file.with_name(
                    f"{input_file.stem}_preprocessed.wav"
                )
            )

        self.save_wav(
            waveform,
            output_path,
            sample_rate,
        )

        duration_seconds = (
            waveform.shape[1] / sample_rate
        )

        return AudioPreprocessResult(
            input_path=str(input_path),
            output_path=str(output_path),
            sample_rate=sample_rate,
            channels=waveform.shape[0],
            duration_seconds=duration_seconds,
            speech_detected=speech_detected,
            vad_applied=True,
            noise_suppression_applied=True,
        )


