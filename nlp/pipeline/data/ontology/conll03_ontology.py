# pylint: disable=unused-wildcard-import, wildcard-import, function-redefined
from nlp.pipeline.data.ontology.base_ontology import *


class Token(Token):  # type: ignore
    def __init__(self, component: str, begin: int, end: int):
        super().__init__(component, begin, end)
        self.chunk_tag = None
        self.ner_tag = None
