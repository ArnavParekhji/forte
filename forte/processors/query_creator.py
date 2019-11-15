# pylint: disable=attribute-defined-outside-init
import pickle

import torch
from texar.torch.hyperparams import HParams
from texar.torch.modules import BERTEncoder
from texar.torch.data import BERTTokenizer

from forte.common.resources import Resources
from forte.data import MultiPack
from forte.processors.base import MultiPackProcessor
from forte.common.types import DataRequest

from forte.data.ontology import Query

__all__ = [
    "QueryCreator"
]


class QueryCreator(MultiPackProcessor):
    r"""This processor searches relevant documents for a query"""

    # pylint: disable=useless-super-delegation
    def __init__(self) -> None:
        super().__init__()

    def initialize(self, resources: Resources, configs: HParams):
        self.resource = resources
        self.config = configs

        self.tokenizer = \
            BERTTokenizer(pretrained_model_name=self.config.tokenizer_model)

        self.device = torch.device("cuda" if torch.cuda.is_available()
                                   else "cpu")

        self.encoder = BERTEncoder(
            pretrained_model_name=None, hparams={"pretrained_model_name": None})

        with open(self.config.model_path, "rb") as f:
            state_dict = pickle.load(f)

        self.encoder.load_state_dict(state_dict["bert"])
        self.encoder.to(self.device)

    # pylint: disable=no-self-use
    def _define_input_info(self) -> DataRequest:
        input_info: DataRequest = {

        }

        return input_info

    # pylint: disable=no-self-use
    def _define_output_info(self) -> DataRequest:
        output_info: DataRequest = {

        }

        return output_info

    @torch.no_grad()
    def get_embeddings(self, inputs, sequence_length, segment_ids):
        output, _ = self.encoder(inputs=inputs,
                                 sequence_length=sequence_length,
                                 segment_ids=segment_ids)
        cls_token = output[:, 0, :]

        return cls_token

    def _process(self, input_pack: MultiPack):

        query_pack = input_pack.get_pack(self.config.query_pack_name)
        context = [query_pack.text]

        # use context to build the query
        if "user_utterance" in input_pack.pack_names:
            user_pack = input_pack.get_pack("user_utterance")
            context.append(user_pack.text)

        if "bot_utterance" in input_pack.pack_names:
            bot_pack = input_pack.get_pack("bot_utterance")
            context.append(bot_pack.text)

        text = ' '.join(context)

        input_ids, segment_ids, input_mask = \
            self.tokenizer.encode_text(
                text_a=text, max_seq_length=self.config.max_seq_length)
        input_ids = torch.LongTensor(input_ids).unsqueeze(0).to(self.device)
        segment_ids = torch.LongTensor(segment_ids).unsqueeze(0).to(self.device)
        input_mask = torch.LongTensor(input_mask).unsqueeze(0).to(self.device)
        sequence_length = (1 - (input_mask == 0)).sum(dim=1)
        query_vector = self.get_embeddings(inputs=input_ids,
                                           sequence_length=sequence_length,
                                           segment_ids=segment_ids)
        query_vector = torch.mean(query_vector, dim=0, keepdim=True)
        query_vector = query_vector.cpu().numpy()
        query = Query(pack=query_pack, value=query_vector)
        query_pack.add_or_get_entry(query)
