"""
This class defines the ontology for Ontonotes dataset
"""
from nlp.pipeline.io.base_ontology import BaseOntology


class OntonotesOntology(BaseOntology):
    class Token(BaseOntology.Token):
        def __init__(self, component: str, begin: int, end: int,
                     tid: str = None):
            super().__init__(component, begin, end, tid)
            self.sense = None
            self.pos_tag = None

    class Sentence(BaseOntology.Sentence):
        def __init__(self, component: str, begin: int, end: int,
                     tid: str = None):
            super().__init__(component, begin, end, tid)
            self.speaker = None
            self.part_id = None

    class PredicateMention(BaseOntology.PredicateMention):
        def __init__(self, component: str, begin: int, end: int,
                     tid: str = None):
            super().__init__(component, begin, end, tid)
            self.pred_type = None
            self.pred_lemma = None
            self.framenet_id = None
