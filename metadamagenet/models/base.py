import abc
from typing import Generic, TypeVar, Optional, Tuple, Dict

from typing_extensions import Self
import torch
from torch import Tensor, nn

from ..logging import log
from .manager import Checkpoint, Metadata, ModelManager
from .unet import UnetBase


class BaseModel(nn.Module, metaclass=abc.ABCMeta):
    def __init__(self):
        super().__init__()
        self.metadata: float = Metadata()

    @classmethod
    def from_pretrained(cls, version: str, seed: int, data_parallel: bool = False) -> Self:
        log(":eyes: loading from checkpoint")
        checkpoint = Checkpoint(
            model_name=cls.name(),
            version=version,
            seed=seed
        )
        manager = ModelManager.get_instance()
        state_dict: dict
        metadata: Metadata
        state_dict, metadata = manager.load_checkpoint(checkpoint)
        empty_model: 'BaseModel' = cls()
        if data_parallel:
            empty_model = nn.DataParallel(empty_model)
        empty_model.load_state_dict(state_dict, strict=True)
        empty_model.metadata = metadata
        return empty_model

    @abc.abstractmethod
    def activate(cls, outputs: Tensor) -> Tensor:
        pass

    @abc.abstractmethod
    def preprocess(self, data: Dict[str, torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        :param data: (Dict[str,torch.Tensor]) raw input data
        :return: (Tuple[torch.Tensor,torch.Tensor]) (inputs,targets)
        """
        pass

    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        pass


UnetType = TypeVar('UnetType', bound=UnetBase)


class Localizer(BaseModel, Generic[UnetType]):

    @classmethod
    def name(cls) -> str:
        return UnetType.name() + "Localizer"

    def __init__(self, unet: Optional[UnetType]):
        super(Localizer, self).__init__()
        self.unet: UnetType = unet if unet is not None else UnetType()
        self.res: nn.Conv2d = nn.Conv2d(in_channels=UnetType.out_channels,
                                        out_channels=1,
                                        kernel_size=1,
                                        stride=1,
                                        padding=0)
        self._initialize_weights()

    def _initialize_weights(self) -> None:
        """
        initialize model weights assuming that unet weights are initialized
        :return:
        """
        self.res.weight.data = nn.init.kaiming_normal_(self.res.weight.data)
        if self.res.bias is not None:
            self.res.bias.data.zero_()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        :param x: float tensor of shape (N,3,H,H)
        :return: float tensor of shape (N,1,H,H)
        """
        return self.res(self.unet(x))

    def activate(cls, outputs: Tensor) -> Tensor:
        return torch.sigmoid(outputs)

    def preprocess(self, data: Dict[str, torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        :param data: {'img': torch.Tensor of shape (N,3,H,H),
                      'msk': torch.Tensor of shape (N,1,H,H)}
        :return: (torch.FloatTensor of shape (N,3,H,H), torch.LongTensor of shape (N,1,H,W)
        """
        return (data['img'] * 2 - 1), data['msk'].long()


class Classifier(BaseModel, Generic[UnetType]):
    @classmethod
    def name(cls) -> str:
        return UnetType.name() + "Classifier"

    def __init__(self, unet: Optional[UnetType]):
        super().__init__()
        self.unet: UnetType = unet if unet is not None else UnetType()
        self.res: nn.Conv2d = nn.Conv2d(in_channels=UnetType.out_channels * 2,
                                        out_channels=5,
                                        kernel_size=1,
                                        stride=1,
                                        padding=0)
        self._initialize_weights()

    def _initialize_weights(self) -> None:
        """
        initialize model weights assuming that unet weights are initialized
        :return:
        """
        self.res.weight.data = nn.init.kaiming_normal_(self.res.weight.data)
        if self.res.bias is not None:
            self.res.bias.data.zero_()

    def forward(self, x: torch.Tensor):
        """
        :param x: float tensor of shape (N,6,H,H)
        :return: float tensor of shape (N,5,H,H)
        """
        pre_disaster_embedding = self.unet(x[:, :3, :, :])
        post_disaster_embedding = self.unet(x[:, 3:, :, :])
        dec10 = torch.cat([pre_disaster_embedding, post_disaster_embedding], dim=1)
        return self.res(dec10)

    def activate(cls, outputs: Tensor) -> Tensor:
        torch.softmax(outputs, dim=1)

    def preprocess(self, data: Dict[str, torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        :param data: {'img_pre': torch.Tensor of shape (N,3,H,H),
                      'img_post': torch.Tensor of shape (N,3,H,H),
                      'msk':torch.Tensor of shape (N,1,H,H)}
        :return: (torch.FloatTensor of shape (N,6,H,H), torch.LongTensor of shape (N,1,H,W)
        """
        return (torch.cat((data['img_pre'] * 2 - 1, data['img_post'] * 2 - 1), dim=1),
                (data['msk'] * 4).long())
