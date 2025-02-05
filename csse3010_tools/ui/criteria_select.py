from textual.widgets import Label, Select
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.message import Message
from textual.suggester import SuggestFromList
from textual.validation import Regex, ValidationResult
from textual import on


class CriteriaSelect(Vertical):
    """Widget that holds 3 dropdowns (year, semester, stage).
    On any child dropdown update, it stops the event and sends a 'Picked' event
    with the combined year/semester/stage.
    """

    class Picked(Message):
        """Fires when the user picks year, semester, or stage."""

        def __init__(self, year: str, semester: str, stage: str) -> None:
            super().__init__()
            self.year = year
            self.semester = semester
            self.stage = stage

    def compose(self) -> ComposeResult:
        # with Horizontal():
        yield Label("Year:")
        yield Select([("2024", "2024")], allow_blank=False, id="year_select")
        # with Horizontal(classes="metadata_field"):
        yield Label("Semester:")
        yield Select([("1", "1")], allow_blank=False, id="semester_select")
        # with Horizontal(classes="metadata_field"):
        yield Label("Stage:")
        yield Select(
            [("pf", "pf")],
            allow_blank=False,
            id="stage_select",
        )
        self.border_title = "Select Stage"

    @on(Select.Changed)
    def child_changed(self, event: Select.Changed) -> None:
        """Whenever any child dropdown changes, dispatch a single new message."""
        event.stop()

        year_val: str = str(self.query_one("#year_select", Select).value)
        sem_val: str = str(self.query_one("#semester_select", Select).value)
        stage_val: str = str(self.query_one("#stage_select", Select).value)

        self.post_message(self.Picked(year_val, sem_val, stage_val))
