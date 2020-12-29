"""Module contains the rawlist prompt."""
from typing import Any, Callable, Dict, List, Literal, Tuple, Union

from prompt_toolkit.filters.base import FilterOrBool
from prompt_toolkit.validation import Validator

from InquirerPy.base import BaseListPrompt, InquirerPyUIControl
from InquirerPy.enum import INQUIRERPY_POINTER_SEQUENCE
from InquirerPy.separator import Separator


class InquirerPyRawlistControl(InquirerPyUIControl):
    """A content control instance intended to used by `prompt_tool_kit` Window.

    All parameter types and purposes, reference `RawlistPrompt`.
    """

    def __init__(
        self,
        choices: Union[Callable[[], List[Any]], List[Any]],
        default: Any,
        pointer: str,
        separator: str,
        marker: str,
    ) -> None:
        """Construct the content control object and add the index to each choice for visual purposes."""
        self._pointer = pointer
        self._separator = separator
        self._marker = marker
        super().__init__(choices, default)

    def _format_choices(self) -> None:
        separator_count = 0
        for index, choice in enumerate(self.choices):
            if isinstance(choice["value"], Separator):
                separator_count += 1
                continue
            choice["display_index"] = index + 1 - separator_count
            choice["actual_index"] = index

        if self.choices:
            first_valid_choice_index = 0
            while isinstance(
                self.choices[first_valid_choice_index]["value"], Separator
            ):
                first_valid_choice_index += 1
            if self.selected_choice_index == first_valid_choice_index:
                for choice in self.choices:
                    if isinstance(choice["value"], Separator):
                        continue
                    if choice["display_index"] == self._default:
                        self.selected_choice_index = choice["actual_index"]
                        break

    def _get_hover_text(self, choice) -> List[Tuple[str, str]]:
        display_choices = []
        display_choices.append(("class:pointer", self._pointer))
        display_choices.append(
            (
                "class:marker",
                self._marker if choice["enabled"] else " ",
            )
        )
        if not isinstance(choice["value"], Separator):
            display_choices.append(
                (
                    "class:pointer",
                    "%s%s " % (str(choice["display_index"]), self._separator),
                )
            )
        display_choices.append(("[SetCursorPosition]", ""))
        display_choices.append(("class:pointer", choice["name"]))
        return display_choices

    def _get_normal_text(self, choice) -> List[Tuple[str, str]]:
        display_choices = []
        display_choices.append(("", len(self._pointer) * " "))
        display_choices.append(
            (
                "class:marker",
                self._marker if choice["enabled"] else " ",
            )
        )
        if not isinstance(choice["value"], Separator):
            display_choices.append(
                ("", "%s%s " % (str(choice["display_index"]), self._separator))
            )
            display_choices.append(("", choice["name"]))
        else:
            display_choices.append(("class:separator", choice["name"]))
        return display_choices


class RawlistPrompt(BaseListPrompt):
    """Used to create a rawlist prompt where user can use number to jump to items.

    :param message: message to display as question
    :type message: str
    :param choices: list of choices available for selection
    :type choices: Union[Callable[[], List[Any]], List[Any]],
    :param default: default value
    :type default: Any
    :param separator: the separator between the index number and the choices
        e.g. default separator is ")"
            1) whatever
            2) whatever
    :type separator: str
    :param style: style for the prompt
    :type style: Dict[str, str]
    :param editing_mode: keybinding mode
    :type editing_mode: Literal["emacs", "vim", "default"]
    :param qmark: question qmark to display
    :type qmark: str
    :param pointer: pointer qmark to display
    :type pointer: str
    :param instruction: instruction to display at the end of the prompt
    :type instruction: str
    :param transformer: a callable to transform the result, this is visual effect only
    :type transformer: Callable
    :param height: preferred height of the choice window
    :type height: Union[str, int]
    :param max_height: max height choice window should reach
    :type max_height: Union[str, int]
    :param multiselect: enable multiselectiion
    :type multiselect: bool
    :param marker: marker symbol to indicate selected choice in multiselect mode
    :type marker: str
    :param validate: a callable or Validator instance to validate user selection
    :type validate: Union[Callable[[str], bool], Validator]
    :param invalid_message: message to display when input is invalid
    :type invalid_message: str
    :param keybindings: custom keybindings to apply
    :type keybindings: Dict[str, List[Dict[str, Union[str, FilterOrBool]]]]
    """

    def __init__(
        self,
        message: str,
        choices: Union[Callable[[], List[Any]], List[Any]],
        default: Any = None,
        separator: str = ")",
        style: Dict[str, str] = None,
        editing_mode: Literal["emacs", "vim", "default"] = "default",
        qmark: str = "?",
        pointer: str = " ",
        instruction: str = "",
        transformer: Callable = None,
        height: Union[int, str] = None,
        max_height: Union[int, str] = None,
        multiselect: bool = False,
        marker: str = INQUIRERPY_POINTER_SEQUENCE,
        validate: Union[Callable[[str], bool], Validator] = None,
        invalid_message: str = "Invalid input",
        keybindings: Dict[str, List[Dict[str, Union[str, FilterOrBool]]]] = None,
    ) -> None:
        """Construct content control and initialise the application while also apply keybindings."""
        self.content_control = InquirerPyRawlistControl(
            choices, default, pointer, separator, marker
        )
        self._instruction = instruction
        super().__init__(
            message=message,
            style=style,
            editing_mode=editing_mode,
            qmark=qmark,
            instruction=instruction,
            transformer=transformer,
            height=height,
            max_height=max_height,
            multiselect=multiselect,
            validate=validate,
            invalid_message=invalid_message,
            keybindings=keybindings,
        )

    def _after_render(self, application) -> None:
        """Override this method to apply custom keybindings.

        Since `self.content_control.choices` may not exists before
        `Application` is created if its a callable, create these
        chocies based keybindings in the after_render call.
        """
        if not self._rendered:
            super()._after_render(application)

            def keybinding_factory(choice):
                @self._register_kb(str(choice["display_index"]))
                def keybinding(_) -> None:
                    self.content_control.selected_choice_index = int(
                        choice["actual_index"]
                    )

                return keybinding

            for choice in self.content_control.choices:
                if not isinstance(choice["value"], Separator):
                    keybinding_factory(choice)

    def _get_prompt_message(self) -> List[Tuple[str, str]]:
        """Return the formatted text to display in the prompt.

        Overriding this method to allow multiple formatted class to be displayed.
        """
        display_message = super()._get_prompt_message()
        if not self.status["answered"] and self.content_control.choices:
            display_message.append(
                (
                    "class:input",
                    " %s" % self.content_control.selection["display_index"]
                    if self.instruction
                    else str(self.content_control.selection["display_index"]),
                )
            )
        return display_message
