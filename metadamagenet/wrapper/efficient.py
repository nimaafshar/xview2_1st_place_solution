import abc
from typing import Optional

import torch
from .wrapper import ModelWrapper, LocalizerModelWrapper, ClassifierModelWrapper
from ..metrics import WeightedImageMetric, DamageF1Score, Dice, ImageMetric
from ..models.unet import EfficientUnetB0, efficientnet_b0
from ..models.unet import Unet


class EfficientUnetB0Wrapper(ModelWrapper, abc.ABC):
    unet_class = EfficientUnetB0
    data_parallel = True

    def empty_unet(self) -> Unet:
        return EfficientUnetB0(efficientnet_b0(pretrained=False))

    def unet_with_pretrained_backbone(self, backbone: Optional[torch.nn.Module] = None) -> Unet:
        if backbone is not None:
            return EfficientUnetB0(backbone)
        return EfficientUnetB0(efficientnet_b0(pretrained=True))


class EfficientUnetB0LocalizerWrapper(EfficientUnetB0Wrapper, LocalizerModelWrapper):
    model_name = "EfficientUnetB0Localizer"
    input_size = (736, 736)

# class Resnet34ClassifierWrapper(Resnet34Wrapper, ClassifierModelWrapper):
#     model_name = "Resnet34UnetClassifier"
#     input_size = (608, 608)
#     default_score: ImageMetric = WeightedImageMetric(
#         ("LocDice", Dice(threshold=0.5, channel=0, inverse=True), 0.3),
#         ("F1", DamageF1Score(), 0.7)
#     )
