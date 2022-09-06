import abc
from typing import Tuple, Type, Union

import torch
from torch import nn

from metadamagenet.models.metadata import Metadata
from metadamagenet.models.unet import Unet, Localizer, Classifier
from metadamagenet.models.checkpoint import Checkpoint
from metadamagenet.models.manager import Manager


class ModelWrapper(abc.ABC):
    @abc.abstractmethod
    @property
    def model_name(self) -> str:
        pass

    @abc.abstractmethod
    @property
    def input_size(self) -> Tuple[int, int]:
        """
        :return: (height,width)
        """
        pass

    @abc.abstractmethod
    @property
    def unet_type(self) -> Union[Type[Localizer], Type[Classifier]]:
        pass

    @abc.abstractmethod
    @property
    def data_parallel(self) -> bool:
        pass

    @abc.abstractmethod
    def empty_unet(self) -> Unet:
        pass

    @abc.abstractmethod
    def unet_with_pretrained_backbone(self, backbone: nn.Module) -> Unet:
        pass

    def from_checkpoint(self, version: str, seed: int) -> Tuple[nn.Module, Metadata]:
        checkpoint = Checkpoint(
            model_name=self.model_name,
            version=version,
            seed=seed
        )
        manager = Manager.get_instance()
        state_dict, metadata = manager.load_checkpoint(checkpoint)
        empty_model: nn.Module = self.unet_type(self.empty_unet)
        if self.data_parallel:
            empty_model = nn.DataParallel(empty_model)
        empty_model.load_state_dict(state_dict, strict=True)
        return empty_model, metadata

    def from_unet(self, unet: Unet) -> Tuple[nn.Module, Metadata]:
        model: nn.Module = self.unet_type(unet)
        if self.data_parallel:
            model = nn.DataParallel(model)
        return model, Metadata()

    def from_backbone(self, backbone: nn.Module) -> Tuple[nn.Module, Metadata]:
        model: nn.Module = self.unet_type(self.unet_with_pretrained_backbone(backbone))
        if self.data_parallel:
            model = nn.DataParallel(model)
        return model, Metadata()

    @abc.abstractmethod
    def apply_activation(self, x: torch.Tensor) -> torch.Tensor:
        pass


class ClassifierModelWrapper(ModelWrapper, abc.ABC):
    unet_type = Classifier


class LocalizerModelWrapper(ModelWrapper, abc.ABC):
    unet_type = Localizer

    def apply_activation(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(x[:, 0, ...])
