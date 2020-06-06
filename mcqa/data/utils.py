import logging
from dataclasses import dataclass
from enum import Enum
from typing import List
from typing import Optional
import tqdm
from transformers import PreTrainedTokenizer

LOGGER = logging.getLogger(__name__)


class Split(Enum):
    train = "train"
    dev = "dev"
    test = "test"


@dataclass(frozen=True)
class InputExample:
    """
    A single training/test example for multiple choice
    Args:
        example_id: Unique id for the example.
        question: string. The untokenized text of the second sequence (question).
        contexts: list of str. The untokenized text of the first sequence
                  (context of corresponding question).
        endings: list of str. multiple choice's options.
                  Its length must be equal to contexts' length.
        label: (Optional) string. The label of the example. This should be
        specified for train and dev examples, but not for test examples.
    """

    example_id: str
    question: str
    contexts: List[str]
    endings: List[str]
    label: Optional[str]


@dataclass(frozen=True)
class InputFeatures:
    """
    A single set of features of data.
    Property names are the same names as the corresponding inputs to a model.
    """

    example_id: str
    input_ids: List[List[int]]
    attention_mask: Optional[List[List[int]]]
    token_type_ids: Optional[List[List[int]]]
    label: Optional[int]


def convert_examples_to_features(examples: List[InputExample],
                                 label_list: List[str], max_length: int,
                                 tokenizer: PreTrainedTokenizer) -> List[InputFeatures]:
    """
    Loads a data file into a list of `InputFeatures`
    """

    label_map = {label: i for i, label in enumerate(label_list)}

    features = []
    for (ex_index, example) in tqdm.tqdm(enumerate(examples), desc="convert examples to features"):
        if ex_index % 10000 == 0:
            LOGGER.info("Writing example %d of %d" % (ex_index, len(examples)))
        choices_inputs = []
        for _, (context, ending) in enumerate(zip(example.contexts,
                                                  example.endings)):
            text_a = context
            if example.question.find("_") != -1:
                # this is for cloze question
                text_b = example.question.replace("_", ending)
            else:
                text_b = example.question + " " + ending

            inputs = tokenizer.encode_plus(
                text_a,
                text_b,
                add_special_tokens=True,
                max_length=max_length,
                pad_to_max_length=True,
                return_overflowing_tokens=True,
            )
            if "num_truncated_tokens" in inputs and inputs["num_truncated_tokens"] > 0:
                LOGGER.info(
                    "Attention! you are cropping tokens (swag task is ok). "
                    "If you are training ARC and RACE and you are poping question + options,"
                    "you need to try to use a bigger max seq length!"
                )

            choices_inputs.append(inputs)

        label = label_map[example.label]

        input_ids = [x["input_ids"] for x in choices_inputs]
        attention_mask = (
            [x["attention_mask"]
                for x in choices_inputs] if "attention_mask" in choices_inputs[0] else None
        )
        token_type_ids = (
            [x["token_type_ids"]
                for x in choices_inputs] if "token_type_ids" in choices_inputs[0] else None
        )

        features.append(
            InputFeatures(
                example_id=example.example_id,
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
                label=label,
            )
        )

    for f in features[:2]:
        LOGGER.info("*** Example ***")
        LOGGER.info("feature: %s" % f)

    return features


def select_field(features, field):
    """Select a field from the features
    Arguments:
        features {InputFeatures} -- List of features : Instances
        of InputFeatures with attribute choice_features being a list
        of dicts.
        field {str} -- Field to consider.
    Returns:
        [list] -- List of corresponding features for field.
    """

    return [
        getattr(feature, field)
        for feature in features
    ]
