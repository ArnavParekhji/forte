import numpy as np
from typing import Dict
from nlp.pipeline.processors.batch_processor import BatchProcessor
from nlp.pipeline.data.data_pack import DataPack
from nlp.pipeline.data.ontology import relation_ontology

__all__ = [
    "DummyRelationExtractor",
]


class DummyRelationExtractor(BatchProcessor):
    """
    A dummy relation extractor
    """

    def __init__(self) -> None:
        super().__init__()

        self.context_type = "sentence"
        self.annotation_types = {
            "Token": [],
            "EntityMention": ["ner_type", "tid"]
        }
        self.batch_size = 4
        self.initialize_batcher()
        self.ontology = relation_ontology

    def predict(self, data_batch: Dict):
        contexts = data_batch["context"]
        entities_span = data_batch["EntityMention"]["span"]
        entities_tid = data_batch["EntityMention"]["tid"]

        pred = {
            "RelationLink": {
                "parent.tid": [],
                "child.tid": [],
                "rel_type": [],
            }
        }
        for context, tid, entity in zip(contexts,
                                        entities_tid,
                                        entities_span):
            parent = []
            child = []
            ner_type = []

            entity_num = len(entity)
            for i in range(entity_num):
                for j in range(i + 1, entity_num):
                    parent.append(tid[i])
                    child.append(tid[j])
                    ner_type.append("dummy_relation")

            pred["RelationLink"]["parent.tid"].append(
                np.array(parent))
            pred["RelationLink"]["child.tid"].append(
                np.array(child))
            pred["RelationLink"]["rel_type"].append(
                np.array(ner_type))

        return pred

    def pack(self, data_pack: DataPack, output_dict: Dict = None):
        """Add corresponding fields to data_pack"""
        if output_dict is None: return

        for i in range(len(output_dict["RelationLink"]["parent.tid"])):
            for j in range(len(output_dict["RelationLink"]["parent.tid"][i])):
                link = self.ontology.RelationLink(
                    component=self.component_name)
                link.rel_type = output_dict["RelationLink"]["rel_type"][i][j]
                link.parent = output_dict["RelationLink"]["parent.tid"][i][j]
                link.child = output_dict["RelationLink"]["child.tid"][i][j]
                data_pack.add_entry(link)

    def _record_fields(self, data_pack: DataPack):
        data_pack.record_fields(
            ["parent", "child", "rel_type"],
            self.ontology.RelationLink.__name__,
            self.component_name,
        )

