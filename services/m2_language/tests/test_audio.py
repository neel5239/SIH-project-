from pathlib import Path
import wave

import torch

from services.m2_language.utils.audio import AudioPreprocessor


AUDIO_DIR = Path("services/m2_language/tests/audio")
INPUT_AUDIO = AUDIO_DIR / "test_converted.wav"
OUTPUT_AUDIO = AUDIO_DIR / "preprocessed_test.wav"


def test_audio_preprocessing():
    assert INPUT_AUDIO.exists(), (
        f"Missing test audio: {INPUT_AUDIO}"
    )

    preprocessor = AudioPreprocessor()

    result = preprocessor.process(
        input_path=str(INPUT_AUDIO),
        output_path=str(OUTPUT_AUDIO),
    )

    assert result.speech_detected is True
    assert result.vad_applied is True
    assert result.noise_suppression_applied is True
    assert result.sample_rate == 16000
    assert result.channels == 1
    assert result.duration_seconds > 0

    assert OUTPUT_AUDIO.exists()
    assert OUTPUT_AUDIO.stat().st_size > 44

    with wave.open(str(OUTPUT_AUDIO), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 16000
        assert wav_file.getsampwidth() == 2
        assert wav_file.getnframes() > 0


def test_mono_conversion():
    preprocessor = AudioPreprocessor()

    stereo = torch.randn(2, 16000)

    mono = preprocessor.convert_to_mono(stereo)

    assert mono.shape == (1, 16000)


def test_resampling():
    preprocessor = AudioPreprocessor()

    waveform = torch.randn(1, 8000)

    resampled, sample_rate = preprocessor.resample(
        waveform,
        8000,
    )

    assert sample_rate == 16000
    assert resampled.shape[1] == 16000


def test_silent_audio_rejected():
    preprocessor = AudioPreprocessor()

    silent_audio = torch.zeros(1, 16000)

    _, speech_detected = preprocessor.apply_vad(
        silent_audio
    )

    assert speech_detected is False


if __name__ == "__main__":
    test_audio_preprocessing()
    test_mono_conversion()
    test_resampling()
    test_silent_audio_rejected()

    print("M2 AUDIO TESTS PASSED")