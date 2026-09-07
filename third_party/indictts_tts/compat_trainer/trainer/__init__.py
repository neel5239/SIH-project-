from dataclasses import dataclass

from coqpit import Coqpit

from torch.nn import Module


# ---------------------------------------------------------------------
# Python 3.12 / Coqpit compatibility
# ---------------------------------------------------------------------

try:
    import compat_coqpit

    compat_coqpit.install()

except Exception:
    pass


# ---------------------------------------------------------------------
# TrainerConfig
# ---------------------------------------------------------------------

@dataclass
class TrainerConfig(Coqpit):
    output_path: str = "output"
    logger_uri: str = None
    run_name: str = "run"
    project_name: str = None
    run_description: str = ""

    print_step: int = 100
    plot_step: int = 100

    epochs: int = 1000

    batch_size: int = 32
    eval_batch_size: int = 32

    mixed_precision: bool = False

    cudnn_enable: bool = True
    cudnn_deterministic: bool = False
    cudnn_benchmark: bool = False

    lr: float = 0.001
    optimizer: str = "Adam"

    num_loader_workers: int = 0
    num_eval_loader_workers: int = 0

    save_step: int = 10000
    save_n_checkpoints: int = 1


# ---------------------------------------------------------------------
# TrainerModel compatibility shim
# ---------------------------------------------------------------------

class TrainerModel:

    def __init__(self, *args, **kwargs):
        super().__init__()

    def state_dict(self, *args, **kwargs):
        """
        Build a PyTorch-style state dictionary from the torch.nn.Module
        components registered directly on the legacy TTS model.
        """

        state = {}

        for name, value in self.__dict__.items():

            if isinstance(value, Module):

                module_state = value.state_dict()

                for key, tensor in module_state.items():
                    state[f"{name}.{key}"] = tensor

        return state

    def load_state_dict(
        self,
        state_dict,
        strict=True,
        assign=False,
    ):
        """
        Compatibility implementation of load_state_dict() for the
        legacy AI4Bharat / Coqui ForwardTTS architecture.
        """

        missing_keys = []
        unexpected_keys = []

        # -------------------------------------------------------------
        # Group checkpoint keys by top-level module.
        # -------------------------------------------------------------

        grouped = {}

        for key, value in state_dict.items():

            if "." in key:
                module_name, sub_key = key.split(".", 1)
            else:
                module_name = key
                sub_key = ""

            grouped.setdefault(module_name, {})[sub_key] = value

        # -------------------------------------------------------------
        # Load each module.
        # -------------------------------------------------------------

        for module_name, module_state in grouped.items():

            module = getattr(self, module_name, None)

            if not isinstance(module, Module):

                for sub_key in module_state:

                    if sub_key:
                        unexpected_keys.append(
                            f"{module_name}.{sub_key}"
                        )
                    else:
                        unexpected_keys.append(module_name)

                continue

            result = module.load_state_dict(
                module_state,
                strict=False,
            )

            for key in result.missing_keys:

                if key:
                    missing_keys.append(
                        f"{module_name}.{key}"
                    )
                else:
                    missing_keys.append(module_name)

            for key in result.unexpected_keys:

                if key:
                    unexpected_keys.append(
                        f"{module_name}.{key}"
                    )
                else:
                    unexpected_keys.append(module_name)

        # -------------------------------------------------------------
        # Create PyTorch-compatible result.
        # -------------------------------------------------------------

        incompatible_keys = type(
            "IncompatibleKeys",
            (),
            {
                "missing_keys": missing_keys,
                "unexpected_keys": unexpected_keys,
            },
        )()

        if strict and (
            missing_keys or unexpected_keys
        ):
            raise RuntimeError(
                "Error(s) in loading state_dict for "
                f"{type(self).__name__}:\n"
                f"\tMissing keys: {missing_keys}\n"
                f"\tUnexpected keys: {unexpected_keys}"
            )

        return incompatible_keys