from dataclasses import asdict, dataclass, field

from coqpit import Coqpit, check_argument

from TTS.config import BaseAudioConfig, BaseDatasetConfig, BaseTrainingConfig


@dataclass
class GSTConfig(Coqpit):
    """Defines the Global Style Token Module."""

    gst_style_input_wav: str = None
    gst_style_input_weights: dict = None
    gst_embedding_dim: int = 256
    gst_use_speaker_embedding: bool = False
    gst_num_heads: int = 4
    gst_num_style_tokens: int = 10

    def check_values(self):
        """Check config fields."""
        c = asdict(self)
        super().check_values()
        check_argument("gst_style_input_weights", c, restricted=False)
        check_argument("gst_style_input_wav", c, restricted=False)
        check_argument(
            "gst_embedding_dim",
            c,
            restricted=True,
            min_val=0,
            max_val=1000,
        )
        check_argument("gst_use_speaker_embedding", c, restricted=False)
        check_argument(
            "gst_num_heads",
            c,
            restricted=True,
            min_val=2,
            max_val=10,
        )
        check_argument(
            "gst_num_style_tokens",
            c,
            restricted=True,
            min_val=1,
            max_val=1000,
        )


@dataclass
class CapacitronVAEConfig(Coqpit):
    """Defines the capacitron VAE Module."""

    capacitron_loss_alpha: int = 1
    capacitron_capacity: int = 150
    capacitron_VAE_embedding_dim: int = 128
    capacitron_use_text_summary_embeddings: bool = True
    capacitron_text_summary_embedding_dim: int = 128
    capacitron_use_speaker_embedding: bool = False
    capacitron_VAE_loss_alpha: float = 0.25
    capacitron_grad_clip: float = 5.0

    def check_values(self):
        """Check config fields."""
        c = asdict(self)
        super().check_values()
        check_argument(
            "capacitron_capacity",
            c,
            restricted=True,
            min_val=10,
            max_val=500,
        )
        check_argument(
            "capacitron_VAE_embedding_dim",
            c,
            restricted=True,
            min_val=16,
            max_val=1024,
        )
        check_argument(
            "capacitron_use_speaker_embedding",
            c,
            restricted=False,
        )
        check_argument(
            "capacitron_text_summary_embedding_dim",
            c,
            restricted=False,
            min_val=16,
            max_val=512,
        )
        check_argument(
            "capacitron_VAE_loss_alpha",
            c,
            restricted=False,
        )
        check_argument(
            "capacitron_grad_clip",
            c,
            restricted=False,
        )


@dataclass
class CharactersConfig(Coqpit):
    """Defines arguments for character/vocabulary configuration."""

    characters_class: str = None

    # Use plain dict instead of typing.Dict.
    # The legacy coqpit deserializer expects concrete classes.
    vocab_dict: dict = None

    pad: str = None
    eos: str = None
    bos: str = None
    blank: str = None
    characters: str = None
    punctuations: str = None
    phonemes: str = None

    is_unique: bool = True
    is_sorted: bool = True


@dataclass
class BaseTTSConfig(BaseTrainingConfig):
    """Shared parameters among all TTS models."""

    # Audio processor configuration.
    audio: BaseAudioConfig = field(default_factory=BaseAudioConfig)

    # Phoneme settings.
    use_phonemes: bool = False
    phonemizer: str = None
    phoneme_language: str = None
    compute_input_seq_cache: bool = False
    text_cleaner: str = None
    enable_eos_bos_chars: bool = False
    test_sentences_file: str = ""
    phoneme_cache_path: str = None

    # Vocabulary parameters.
    characters: CharactersConfig = None
    add_blank: bool = False

    # Training parameters.
    batch_group_size: int = 0
    loss_masking: bool = None

    # Data loading.
    sort_by_audio_len: bool = False
    min_audio_len: int = 1
    max_audio_len: int = float("inf")
    min_text_len: int = 1
    max_text_len: int = float("inf")

    compute_f0: bool = False
    compute_linear_spec: bool = False
    precompute_num_workers: int = 0
    use_noise_augment: bool = False
    start_by_longest: bool = False

    # Dataset.
    #
    # IMPORTANT:
    # Do not use typing.List here.
    # Legacy coqpit 0.0.17 can call issubclass() on typing.List,
    # which fails on Python 3.12.
    datasets: list = field(
        default_factory=lambda: [BaseDatasetConfig()]
    )

    # Optimizer.
    optimizer: str = "radam"
    optimizer_params: dict = None

    # Scheduler.
    lr_scheduler: str = ""
    lr_scheduler_params: dict = field(default_factory=dict)

    # Testing.
    #
    # Use plain list instead of typing.List[str] for Python 3.12
    # compatibility with legacy coqpit.
    test_sentences: list = field(default_factory=list)

    # Evaluation.
    eval_split_max_size: int = None
    eval_split_size: float = 0.01

    # Weighted samplers.
    use_speaker_weighted_sampler: bool = False
    speaker_weighted_sampler_alpha: float = 1.0

    use_language_weighted_sampler: bool = False
    language_weighted_sampler_alpha: float = 1.0

    use_length_weighted_sampler: bool = False
    length_weighted_sampler_alpha: float = 1.0