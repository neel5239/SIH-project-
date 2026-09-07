from dataclasses import dataclass, field
from typing import List

from TTS.tts.configs.shared_configs import BaseTTSConfig
from TTS.tts.models.forward_tts import ForwardTTSArgs


@dataclass
class FastPitchConfig(BaseTTSConfig):
    """Configure ForwardTTS as FastPitch model.

    FastPitch is implemented using the ForwardTTS model architecture.
    """

    model: str = "fast_pitch"
    base_model: str = "forward_tts"

    # Model-specific parameters
    #
    # Python 3.12 requires mutable dataclass defaults to use
    # default_factory rather than ForwardTTSArgs().
    model_args: ForwardTTSArgs = field(default_factory=ForwardTTSArgs)

    # Multi-speaker settings
    num_speakers: int = 0
    speakers_file: str = None
    use_speaker_embedding: bool = False
    use_d_vector_file: bool = False
    d_vector_file: str = False
    d_vector_dim: int = 0

    # Optimizer parameters
    optimizer: str = "Adam"
    optimizer_params: dict = field(
        default_factory=lambda: {
            "betas": [0.9, 0.998],
            "weight_decay": 1e-6,
        }
    )

    lr_scheduler: str = "NoamLR"
    lr_scheduler_params: dict = field(
        default_factory=lambda: {
            "warmup_steps": 4000,
        }
    )

    lr: float = 1e-4
    grad_clip: float = 5.0

    # Loss parameters
    spec_loss_type: str = "mse"
    duration_loss_type: str = "mse"

    use_ssim_loss: bool = True
    ssim_loss_alpha: float = 1.0

    spec_loss_alpha: float = 1.0
    aligner_loss_alpha: float = 1.0
    pitch_loss_alpha: float = 0.1
    dur_loss_alpha: float = 0.1

    binary_align_loss_alpha: float = 0.1
    binary_loss_warmup_epochs: int = 150

    # Sequence parameters
    min_seq_len: int = 13
    max_seq_len: int = 200

    # Reduction factor
    r: int = 1

    # F0 cache
    f0_cache_path: str = None