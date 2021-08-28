"""Contains the base class :class:`.BaseListPrompt` which can be used to create a prompt involving choices."""
import asyncio
from abc import abstractmethod
from typing import Any, Callable, Dict, List, Union

from prompt_toolkit.filters.base import Condition, FilterOrBool
from prompt_toolkit.keys import Keys
from prompt_toolkit.validation import Validator

from InquirerPy.base.complex import BaseComplexPrompt
from InquirerPy.base.control import InquirerPyUIListControl
from InquirerPy.separator import Separator
from InquirerPy.utils import InquirerPyStyle, SessionResult


class BaseListPrompt(BaseComplexPrompt):
    """A base class to create a complex prompt involving choice selections (i.e. list) using `prompt_toolkit` Application.

    Note:
        This class does not create :class:`~prompt_toolkit.layout.Layout` nor :class:`~prompt_toolkit.application.Application`,
        it only contains the necessary attributes and helper functions to be consumed.

    See Also:
        :class:`~InquirerPy.prompts.list.ListPrompt`
        :class:`~InquirerPy.prompts.fuzzy.FuzzyPrompt`
    """

    def __init__(
        self,
        message: Union[str, Callable[[SessionResult], str]],
        style: InquirerPyStyle = None,
        vi_mode: bool = False,
        qmark: str = "?",
        amark: str = "?",
        instruction: str = "",
        transformer: Callable[[Any], Any] = None,
        filter: Callable[[Any], Any] = None,
        validate: Union[Callable[[Any], bool], Validator] = None,
        invalid_message: str = "Invalid input",
        multiselect: bool = False,
        keybindings: Dict[str, List[Dict[str, Union[str, FilterOrBool]]]] = None,
        cycle: bool = True,
        wrap_lines: bool = True,
        spinner_enable: bool = False,
        spinner_pattern: List[str] = None,
        spinner_text: str = "",
        spinner_delay: float = 0.1,
        set_exception_handler: bool = True,
        session_result: SessionResult = None,
    ) -> None:
        super().__init__(
            message=message,
            style=style,
            vi_mode=vi_mode,
            qmark=qmark,
            amark=amark,
            transformer=transformer,
            filter=filter,
            invalid_message=invalid_message,
            validate=validate,
            instruction=instruction,
            wrap_lines=wrap_lines,
            spinner_enable=spinner_enable,
            spinner_pattern=spinner_pattern,
            spinner_delay=spinner_delay,
            spinner_text=spinner_text,
            set_exception_handler=set_exception_handler,
            session_result=session_result,
        )

        if not keybindings:
            keybindings = {}

        self._content_control: InquirerPyUIListControl
        self._multiselect = multiselect
        self._is_multiselect = Condition(lambda: self._multiselect)
        self._cycle = cycle

        self.kb_maps = {
            "down": [
                {"key": "down"},
                {"key": "c-n", "filter": ~self._is_vim_edit},
                {"key": "j", "filter": self._is_vim_edit},
            ],
            "up": [
                {"key": "up"},
                {"key": "c-p", "filter": ~self._is_vim_edit},
                {"key": "k", "filter": self._is_vim_edit},
            ],
            "toggle": [
                {"key": "space", "filter": self._is_multiselect},
            ],
            "toggle-down": [
                {"key": Keys.Tab, "filter": self._is_multiselect},
            ],
            "toggle-up": [
                {"key": Keys.BackTab, "filter": self._is_multiselect},
            ],
            "toggle-all": [
                {"key": "alt-r", "filter": self._is_multiselect},
            ],
            "toggle-all-true": [
                {"key": "alt-a", "filter": self._is_multiselect},
            ],
            "toggle-all-false": [],
            **keybindings,
        }

        self.kb_func_lookup = {
            "down": [{"func": self._handle_down}],
            "up": [{"func": self._handle_up}],
            "toggle": [{"func": self._toggle_choice}],
            "toggle-down": [{"func": self._toggle_choice}, {"func": self._handle_down}],
            "toggle-up": [{"func": self._toggle_choice}, {"func": self._handle_up}],
            "toggle-all": [{"func": self._toggle_all}],
            "toggle-all-true": [{"func": self._toggle_all, "args": [True]}],
            "toggle-all-false": [{"func": self._toggle_all, "args": [False]}],
        }

    def _on_rendered(self, _) -> None:
        """Fetch all the choices and perform post processing after UI is rendered."""
        if self.content_control._choice_func:
            self.loading = True
            task = asyncio.create_task(self.content_control.retrieve_choices())
            task.add_done_callback(self._choices_callback)
        else:
            self._choices_callback(None)

    def _choices_callback(self, _) -> None:
        """Perform actions once all choices are retrieved."""
        self._redraw()

    @property
    def content_control(self) -> InquirerPyUIListControl:
        """Get the content controller object.

        Needs to be an instance of :class:`~InquirerPy.base.control.InquirerPyUIListControl`.

        Each :class:`.BaseComplexPrompt` requires a `content_control` to display custom
        contents for the prompt.

        Raises:
            NotImplementedError: When `self._content_control` is not found.
        """
        if not self._content_control:
            raise NotImplementedError
        return self._content_control

    @content_control.setter
    def content_control(self, value: InquirerPyUIListControl) -> None:
        self._content_control = value

    @property
    def loading(self) -> bool:
        """bool: Indicate if the prompt is loading."""
        return self.content_control.loading

    @loading.setter
    def loading(self, value: bool) -> None:
        self.content_control.loading = value
        if self.loading:
            asyncio.create_task(self._spinner.start())

    @property
    def result_name(self) -> Any:
        """Get the result value that should be printed to the terminal.

        In multiselect scenario, return result as a list.
        """
        if self._multiselect:
            return [choice["name"] for choice in self.selected_choices]
        else:
            try:
                return self.content_control.selection["name"]
            except IndexError:
                return ""

    @property
    def result_value(self) -> Any:
        """Get the result value that should return to the user.

        In multiselect scenario, return result as a list.
        """
        if self._multiselect:
            return [choice["value"] for choice in self.selected_choices]
        else:
            try:
                return self.content_control.selection["value"]
            except IndexError:
                return ""

    @property
    def selected_choices(self) -> List[Any]:
        """List[Any]: Get all user selected choices."""

        def filter_choice(choice):
            return not isinstance(choice, Separator) and choice["enabled"]

        return list(filter(filter_choice, self.content_control.choices))

    def _handle_down(self) -> bool:
        """Handle event when user attempts to move down.

        Returns:
            Boolean indicating if the action hits the cap.
        """
        if self._cycle:
            self.content_control.selected_choice_index = (
                self.content_control.selected_choice_index + 1
            ) % self.content_control.choice_count
            return False
        else:
            self.content_control.selected_choice_index += 1
            if (
                self.content_control.selected_choice_index
                >= self.content_control.choice_count
            ):
                self.content_control.selected_choice_index = (
                    self.content_control.choice_count - 1
                )
                return True
            return False

    def _handle_up(self) -> bool:
        """Handle event when user attempts to move up.

        Returns:
            Boolean indicating if the action hits the cap.
        """
        if self._cycle:
            self.content_control.selected_choice_index = (
                self.content_control.selected_choice_index - 1
            ) % self.content_control.choice_count
            return False
        else:
            self.content_control.selected_choice_index -= 1
            if self.content_control.selected_choice_index < 0:
                self.content_control.selected_choice_index = 0
                return True
            return False

    @abstractmethod
    def _toggle_choice(self) -> None:
        """Handle event when user attempting to toggle the state of the chocie."""
        pass

    @abstractmethod
    def _toggle_all(self, value: bool) -> None:
        """Handle event when user attempting to alter the state of all choices."""
        pass
