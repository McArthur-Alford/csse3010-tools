from textual.widgets import Label, Input
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.message import Message
from textual.suggester import SuggestFromList
from textual.validation import Regex, ValidationResult
from textual import on

class StudentNumber(Input):
    DEFAULT_CLASSES="metadata_field"

    """Input widget for student number."""
    class Updated(Message):
        """Fires when the student number is changed and is valid."""
        def __init__(self, number: str) -> None:
            self.number = number
            super().__init__()
    
    student_numbers: reactive[list[str]] = reactive([])

    def on_mount(self):
        self.Changed.bubble = False
        self.placeholder = "sXXXXXXX"
        self.validators = [Regex(r"s\d{7}")]

    def watch_student_numbers(self, old: list[str], new: list[str]):
        self.suggester = SuggestFromList(new, case_sensitive=False)

    @on(Input.Changed)
    def validate_and_update(self, event: Input.Changed) -> None:
        """Checks validation, posts an Updated event if valid."""
        if event.validation_result is not None and not event.validation_result.is_valid:
            self.add_class("invalid")
        else:
            self.remove_class("invalid")
            # Fire our custom "StudentNumber.Updated" event
            self.post_message(self.Updated(event.value))


class StudentSelect(Horizontal):
    DEFAULT_CLASSES="metadata_field"
    
    """A container for label + StudentNumber in a single row."""
    def compose(self) -> ComposeResult:
        with Horizontal(classes="metadata_field"):
            yield Label("Student Number:")
            yield StudentNumber()
