from abc import abstractmethod
from typing import Dict, Iterator

from nlp.pipeline.common.resources import Resources
from nlp.pipeline.processors.base_processor import BaseProcessor

__all__ = [
    "Trainer",
]


class Trainer(BaseProcessor):
    def __init__(self, config):  # pylint: disable=unused-argument
        super().__init__()
        self.__stop_train = False
        self.__validation_requested = False
        self.__dev_eval_result = None

    def initialize(self, resources: Resources):
        pass

    def validation_requested(self) -> bool:
        return self.__validation_requested

    def stop_train(self) -> bool:
        return self.__stop_train

    @abstractmethod
    def data_request(self):
        pass

    @abstractmethod
    def process(self, instance: Dict):
        # Do training
        raise NotImplementedError

    def get_loss(self, instances: Iterator[Dict]):
        raise NotImplementedError

    def pack_finish_action(self, pack_count: int):
        pass

    def epoch_finish_action(self, epoch_num: int):
        pass

    def request_eval(self):
        self.__validation_requested = True

    def _eval_call_back(self, eval_result):
        self.__dev_eval_result = eval_result
        self.__validation_requested = False
