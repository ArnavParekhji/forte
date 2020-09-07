# Copyright 2019 The Forte Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Unit tests for OpenIEReader.
"""
import os
import unittest
from typing import Iterator, Iterable

from forte.data.readers import OpenIEReader
from forte.data.data_pack import DataPack
from forte.pipeline import Pipeline
from ft.onto.base_ontology import Sentence, PredicateMention, Document, \
    PredicateArgument, PredicateLink


class OpenIEReaderTest(unittest.TestCase):

    def setUp(self):
        # Define and config the pipeline.
        self.dataset_path = os.path.abspath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            *([os.path.pardir] * 4),
            'data_samples/openie'))

        self.pipeline = Pipeline[DataPack]()
        self.reader = OpenIEReader()
        self.pipeline.set_reader(self.reader)
        self.pipeline.initialize()

    def test_process_next(self):
        data_packs: Iterable[DataPack] = self.pipeline.process_dataset(
            self.dataset_path)
        file_paths: Iterator[str] = self.reader._collect(self.dataset_path)

        count_packs = 0

        for pack, file_path in zip(data_packs, file_paths):
            count_packs += 1
            expected_doc: str = ""
            with open(file_path, "r", encoding="utf8", errors='ignore') as file:
                expected_doc = file.read()

            # Test document.
            actual_docs = list(pack.get(Document))
            self.assertEqual(len(actual_docs), 1)
            actual_doc = actual_docs[0]
            self.assertEqual(actual_doc.text, expected_doc.replace('\t', ' ').replace('\n', ' ') + ' ')

            lines = expected_doc.split('\n')
            actual_sentences = pack.get(Sentence)
            actual_predicates = pack.get(PredicateMention)
            actual_args = pack.get(PredicateArgument)
            actual_links = pack.get(PredicateLink)

            for line in lines:
                line = line.strip().split('\t')

                # Test sentence.
                expected_sentence = line[0]
                actual_sentence = next(actual_sentences)
                self.assertEqual(actual_sentence.text, expected_sentence)

                # Test predicate.
                expected_predicate = line[1]
                actual_predicate = next(actual_predicates)
                self.assertEqual(actual_predicate.text, expected_predicate)

                # Test argument.
                for expected_arg in line[2:]:
                    actual_arg = next(actual_args)
                    self.assertEqual(actual_arg.text, expected_arg)

                    # Test predicate relation link.
                    actual_link = next(actual_links)
                    self.assertEqual(actual_link.get_parent().text, expected_predicate)
                    self.assertEqual(actual_link.get_child().text, expected_arg)

        self.assertEqual(count_packs, 1)


if __name__ == '__main__':
    unittest.main()
