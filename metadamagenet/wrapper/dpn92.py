import abc
from typing import Tuple
from torch import nn

from .wrapper import ModelWrapper, LocalizerModelWrapper, ClassifierModelWrapper
from metadamagenet.models.unet import Unet
from metadamagenet.models.metadata import Metadata
from metadamagenet.models.checkpoint import Checkpoint
from metadamagenet.models.manager import Manager
from metadamagenet.models.unet import Dpn92Unet
from metadamagenet.models.dpn import DPN,dpn92


class SeResnext50Wrapper(ModelWrapper, abc.ABC):
    pass


class SeResnext50LocalizerWrapper(SeResnext50Wrapper, LocalizerModelWrapper):
    @property
    def model_name(self) -> str:
        return "SeResnext50UnetLocalizer"

    def from_checkpoint(self, version: str, seed: int) -> Tuple[nn.Module, Metadata]:
        checkpoint = Checkpoint(
            model_name=self.model_name,
            version=version,
            seed=seed
        )
        manager = Manager.get_instance()
        state_dict, metadata = manager.load_checkpoint(checkpoint)
        empty_model: nn.Module = self.unet_type(Dpn92Unet(dpn92(pretrained=None)))
        empty_model.load_state_dict(state_dict, strict=True)
        return empty_model, metadata

    def from_unet(self, unet: Unet) -> Tuple[nn.Module, Metadata]:
        return self.unet_type(unet), Metadata()

    def from_backbone(self, backbone: DPN) -> Tuple[nn.Module, Metadata]:
        return self.unet_type(Dpn92Unet(backbone)), Metadata()


class SeResnext50ClassifierWrapper(SeResnext50Wrapper, ClassifierModelWrapper):

    @property
    def model_name(self) -> str:
        return "SeResnext50UnetClassifier"

    def from_checkpoint(self, version: str, seed: int) -> Tuple[nn.Module, Metadata]:
        checkpoint = Checkpoint(
            model_name=self.model_name,
            version=version,
            seed=seed
        )
        manager = Manager.get_instance()
        state_dict, metadata = manager.load_checkpoint(checkpoint)
        empty_model: nn.Module = nn.DataParallel(self.unet_type(Dpn92Unet(dpn92(pretrained=None))))
        empty_model.load_state_dict(state_dict, strict=True)
        return empty_model, metadata

    def from_unet(self, unet: Unet) -> Tuple[nn.Module, Metadata]:
        return nn.DataParallel(self.unet_type(unet)), Metadata()

    def from_backbone(self, backbone: DPN) -> Tuple[nn.Module, Metadata]:
        return nn.DataParallel((self.unet_type(Dpn92Unet(backbone)))), Metadata()
