from typing import Any, Union

import hydra
import pytorch_lightning as pl
import torch
from omegaconf import DictConfig

from src.data.labels import Labels
from src.data.model_inputs import ModelInputs


class PLModule(pl.LightningModule):
    def __init__(
        self,
        model: Union[torch.nn.Module, DictConfig],
        labels: Labels = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__()
        self.save_hyperparameters()
        self.labels = labels
        if isinstance(model, DictConfig):
            self.model = hydra.utils.instantiate(model, labels=labels)
        else:
            self.model = model

    def forward(self, **kwargs) -> dict:
        """
        Method for the forward pass.
        'training_step', 'validation_step' and 'test_step' should call
        this method in order to compute the output predictions and the loss.

        Returns:
            output_dict: forward output containing the predictions (output logits ecc...) and the loss if any.

        """
        return self.model(**kwargs)

    def training_step(self, batch: ModelInputs, batch_idx: int) -> torch.Tensor:
        forward_output = self.forward(**batch, return_loss=True)
        self.log("loss", forward_output["loss"])
        return forward_output["loss"]

    def validation_step(self, batch: ModelInputs, batch_idx: int) -> None:
        forward_output = self.forward(**batch, return_loss=True)
        self.log("val_loss", forward_output["loss"])

    def test_step(self, batch: ModelInputs, batch_idx: int) -> Any:
        forward_output = self.forward(**batch, return_loss=True)
        self.log("test_loss", forward_output["loss"])

    def configure_optimizers(self):
        # TODO: parametrize this stuff
        # if "grouped_parameters" in self.hparams and self.hparams.grouped_parameters:
        #     param_optimizer = list(self.named_parameters())
        #     no_decay = ["bias", "LayerNorm.bias", "LayerNorm.weight"]
        #     optimizer_grouped_parameters = [
        #         {
        #             "params": [
        #                 p
        #                 for n, p in param_optimizer
        #                 if "language_model" in n and not any(nd in n for nd in no_decay)
        #             ],
        #             "weight_decay": self.hparams.optimizer.weight_decay,
        #         },
        #         {
        #             "params": [
        #                 p
        #                 for n, p in param_optimizer
        #                 if "language_model" in n and any(nd in n for nd in no_decay)
        #             ],
        #             "weight_decay": 0.0,
        #         },
        #     ]
        # else:
        optimizer_grouped_parameters = self.parameters()
        optimizer = hydra.utils.instantiate(
            self.hparams.optimizer,
            params=optimizer_grouped_parameters,
            _convert_="partial",
        )
        if "lr_scheduler" not in self.hparams or not self.hparams.lr_scheduler:
            return optimizer

        lr_scheduler_config = {
            "scheduler": hydra.utils.instantiate(
                self.hparams.lr_scheduler, optimizer=optimizer
            ),
            "interval": "step",
            "frequency": 1,
        }
        return [optimizer], [lr_scheduler_config]
