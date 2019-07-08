from abc import abstractmethod
from typing import Dict, Any, List
from nlp.pipeline.data.data_pack import DataPack
from nlp.pipeline.utils import *

__all__ = [
    "BaseProcessor",
]


class BaseProcessor:
    def __init__(self):
        # Initialized model.
        self.component_name = get_full_component_name(self)
        self.context_type = None
        self.annotation_types = None
        self.link_types = None
        self.group_types = None
        self.batch_size = None

    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def process(self, *inputs):
        # Do testing or training
        pass

    @abstractmethod
    def finish(self):
        # Release model.
        pass
