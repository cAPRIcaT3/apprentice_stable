"""Implementation derived from https://github.com/tloen/alpaca-lora"""
import sys
from pathlib import Path

# support running without installing as a package
wd = Path(__file__).parent.parent.parent.resolve()
print(wd)
sys.path.append(str(wd))

import torch
import requests
import json
from torch.utils.data import random_split
from lit_llama.tokenizer import Tokenizer
from tqdm import tqdm


DATA_FILE = "https://raw.githubusercontent.com/tloen/alpaca-lora/main/alpaca_data_cleaned_archive.json"
DATA_FILE_NAME1 = "train.json"
DATA_FILE_NAME2 = "val.json"
IGNORE_INDEX = -1


def prepare(
    destination_path: Path = Path("data/alpaca"), 
    tokenizer_path: Path = Path("checkpoints/lit-llama/tokenizer.model"),
    test_split_size: int = 3000,
    max_seq_length: int = 2048,
    seed: int = 42,
    mask_inputs: bool = False,  # as in alpaca-lora
    data_file_name1: str = DATA_FILE_NAME1,
    data_file_name2: str = DATA_FILE_NAME2
) -> None:
    """Prepare the Alpaca dataset for instruction tuning.
    
    The output is a training and validation dataset saved as `train.pt` and `val.pt`,
    which stores the preprocessed and tokenized prompts and labels.
    """
    
    destination_path.mkdir(parents=True, exist_ok=True)
    file_path1 = destination_path / data_file_name1
    file_path2 = destination_path / data_file_name2
    # download(file_path)

    # TODO: If we don't have the Meta weights, where do we get the tokenizer from?
    tokenizer = Tokenizer(tokenizer_path)
    
    with open(file_path1, "r") as file:
        data1 = json.load(file)
    with open(file_path2, "r") as file:
        data2 = json.load(file)

    # Partition the dataset into train and test
    train_set, validation_set = list(data1), list(data2)

    print(f"train has {len(train_set):,} samples")
    print(f"val has {len(validation_set):,} samples")

    print("Processing train split ...")
    train_set = [prepare_sample(sample, tokenizer, max_seq_length, mask_inputs) for sample in tqdm(train_set)]
    torch.save(train_set, file_path1.parent / "train.pt")

    print("Processing val split ...")
    validation_set = [prepare_sample(sample, tokenizer, max_seq_length, mask_inputs) for sample in tqdm(validation_set)]
    torch.save(validation_set, file_path1.parent / "validation.pt")


def download(file_path: Path):
    """Downloads the raw json data file and saves it in the given destination."""
    if file_path.exists():
        return
    with open(file_path, "w") as f:
        f.write(requests.get(DATA_FILE).text)


def prepare_sample(example: dict, tokenizer: Tokenizer, max_length: int, mask_inputs: bool = True):
    """Processes a single sample.
    
    Each sample in the dataset consists of:
    - instruction: A string describing the task
    - input: A string holding a special input value for the instruction.
        This only applies to some samples, and in others this is empty.
    - output: The response string

    This function processes this data to produce a prompt text and a label for
    supervised training. The prompt text is formed as a single message including both
    the instruction and the input. The label/target is the same message but with the
    response attached.

    Finally, both the prompt and the label get tokenized. If desired, all tokens
    in the label that correspond to the original input prompt get masked out (default).
    """
    full_prompt = generate_prompt(example)
    full_prompt_and_response = full_prompt + example["output"]

    # Tokenize the prompt and the prompt with response
    # First examine the total token length of the prompt and response
    encoded_full_prompt_and_response = tokenizer.my_encode_for_prompt_and_output(full_prompt_and_response, bos=True, eos=True, max_length=max_length)
    # if not exceed max_length, then we can use the original tokens
    if encoded_full_prompt_and_response is not None:
        encoded_full_prompt = tokenize(tokenizer, full_prompt, max_length=max_length, eos=False)
    # else we need to truncate the tokens of the input prompt
    else:
        encoded_full_prompt = [tokenizer.bos_id] + tokenizer.processor.encode(full_prompt[:-len("\n\n### Response:\n")])
        encoded_response = tokenizer.processor.encode("\n\n### Response:\n" + example["output"]) + [tokenizer.eos_id]
        # truncate the input prompt since the total length exceeds max_length
        if len(encoded_response) <= max_length//2:
            encoded_full_prompt = encoded_full_prompt[:max_length - len(encoded_response)]
            encoded_full_prompt_and_response = encoded_full_prompt + encoded_response
        elif len(encoded_full_prompt) <= max_length//2:
            encoded_response = encoded_response[:max_length - len(encoded_full_prompt)]
            encoded_full_prompt_and_response = encoded_full_prompt + encoded_response
        else:
            encoded_full_prompt = encoded_full_prompt[:max_length//2]
            encoded_response = encoded_response[:max_length//2]
            encoded_full_prompt_and_response = encoded_full_prompt + encoded_response
        assert len(encoded_full_prompt_and_response) <= max_length
        encoded_full_prompt = torch.tensor(encoded_full_prompt, dtype=torch.int, device=None)
        encoded_full_prompt_and_response = torch.tensor(encoded_full_prompt_and_response, dtype=torch.int, device=None)
    # encoded_full_prompt = tokenize(tokenizer, full_prompt, max_length=max_length, eos=False)
    # encoded_full_prompt_and_response = tokenize(tokenizer, full_prompt_and_response, eos=True, max_length=max_length)

    # The labels are the full prompt with response, but with the prompt masked out
    labels = encoded_full_prompt_and_response.clone()
    if mask_inputs:
        labels[:len(encoded_full_prompt)] = IGNORE_INDEX

    return {**example, "input_ids": encoded_full_prompt_and_response, "input_ids_no_response": encoded_full_prompt, "labels": labels}


def tokenize(tokenizer: Tokenizer, string: str, max_length: int, eos=True) -> torch.Tensor:
    return tokenizer.encode(string, bos=True, eos=eos, max_length=max_length)


def generate_prompt(example):
    """Generates a standardized message to prompt the model with an instruction, optional input and a
    'response' field."""

    if example["input"]:
        return (
            "Below is an instruction that describes a task, paired with an input that provides further context. "
            "Write a response that appropriately completes the request.\n\n"
            f"### Instruction:\n{example['instruction']}\n\n### Input:\n{example['input']}\n\n### Response:\n"
        )
    return (
        "Below is an instruction that describes a task. "
        "Write a response that appropriately completes the request.\n\n"
        f"### Instruction:\n{example['instruction']}\n\n### Response:\n"
    )


if __name__ == "__main__":
    from jsonargparse import CLI

    CLI(prepare)