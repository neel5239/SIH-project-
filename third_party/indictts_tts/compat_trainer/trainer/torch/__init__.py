from torch.utils.data.distributed import DistributedSampler


class DistributedSamplerWrapper(DistributedSampler):
    """
    Minimal compatibility implementation for legacy Coqui TTS inference.

    The historical Trainer package exposed this class from trainer.torch.
    For inference, the standard PyTorch DistributedSampler behavior is
    sufficient.
    """

    pass