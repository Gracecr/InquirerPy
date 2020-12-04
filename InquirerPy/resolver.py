"""This module contains the main prompt entrypoint."""
import os
from typing import Any, Dict, List, Literal, Optional, Union

from InquirerPy.base import ACCEPTED_KEYBINDINGS
from InquirerPy.exceptions import InvalidArgument, RequiredKeyNotFound
from InquirerPy.prompts.checkbox import CheckboxPrompt
from InquirerPy.prompts.confirm import ConfirmPrompt
from InquirerPy.prompts.filepath import FilePathPrompt
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.prompts.secret import SecretPrompt

question_mapping = {
    "confirm": ConfirmPrompt,
    "filepath": FilePathPrompt,
    "secret": SecretPrompt,
    "input": InputPrompt,
    "list": ListPrompt,
    "checkbox": CheckboxPrompt,
}


def prompt(
    questions: List[Dict[str, Any]],
    style: Optional[Dict[str, str]] = None,
    editing_mode: Optional[Literal["default", "vim", "emacs"]] = None,
) -> Dict[str, Optional[Union[str, List[str], bool]]]:
    """Resolve user provided list of questions and get result.

    :param questions: list of questions to ask
    :type questions: List[Dict[str, Any]]
    :param style: the style to apply to the prompt
    :type style: Optional[Dict[str, str]]
    :param editing_mode: the editing_mode to use
    :type editing_mode: Optional[str]
    :return: dictionary of answers
    :rtype: Dict[str, Optional[Union[str, List[str], bool]]]
    """
    result: Dict[str, Optional[Union[str, List[str], bool]]] = {}

    if not isinstance(questions, list):
        raise InvalidArgument("questions should be type of list.")

    if not style:
        style = {
            "symbol": os.getenv("INQUIRERPY_STYLE_SYMBOL", "#e5c07b"),
            "answer": os.getenv("INQUIRERPY_STYLE_ANSWER", "#61afef"),
            "input": os.getenv("INQUIRERPY_STYLE_INPUT", "#98c379"),
            "question": os.getenv("INQUIRERPY_STYLE_QUESTION", ""),
            "instruction": os.getenv("INQUIRERPY_STYLE_INSTRUCTION", ""),
            "pointer": os.getenv("INQUIRERPY_STYLE_POINTER", "#61afef"),
            "enabled": os.getenv("INQUIRERPY_STYLE_ENABLED", "#e5c07b"),
        }
    if not editing_mode:
        default_mode = os.getenv("INQUIRERPY_EDITING_MODE", "default")
        if default_mode not in ACCEPTED_KEYBINDINGS:
            raise InvalidArgument(
                "INQUIRERPY_EDITING_MODE must be one of 'default' 'emacs' 'vim'."
            )
        else:
            editing_mode = default_mode  # type: ignore

    for i in range(len(questions)):
        try:
            question_type = questions[i].pop("type")
            question_name = questions[i].pop("name", str(i))
            question_content = questions[i].pop("question")
            if questions[i].get("condition") and not questions[i]["condition"](result):
                result[question_name] = None
                continue
            result[question_name] = question_mapping[question_type](
                message=question_content,
                style=style,
                editing_mode=editing_mode,
                **questions[i]
            ).execute()
            if result[question_name] == "INQUIRERPY_KEYBOARD_INTERRUPT":
                raise KeyboardInterrupt
        except KeyError:
            raise RequiredKeyNotFound

    return result
