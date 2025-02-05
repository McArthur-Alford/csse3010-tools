from typing import Optional, List

from textual.app import ComposeResult
from textual.containers import Grid, VerticalScroll, Container
from textual.message import Message
from textual.widgets import (
    Button,
    Collapsible,
    Input,
    Placeholder,
    Static,
    TextArea,
    Label,
)

from csse3010_tools.rubric import Task, Rubric


class MarkSelected(Message):
    """Message indicating a mark button has been selected."""

    def __init__(self, task_name: str, band_name: str, chosen_mark: int) -> None:
        super().__init__()
        self.task_name = task_name
        self.band_name = band_name
        self.chosen_mark = chosen_mark


class MarkButton(Button):
    """
    A button representing a particular mark for a (task_name, band_name).
    """

    def __init__(
        self,
        label: str,
        task_name: str,
        band_name: str,
        chosen_mark: int,
        *args,
        **kwargs,
    ):
        super().__init__(label, *args, **kwargs)
        self.task_name = task_name
        self.band_name = band_name
        self.chosen_mark = chosen_mark

    def on_click(self) -> None:
        """
        Post a MarkSelected event when clicked.
        """
        self.post_message(
            MarkSelected(
                task_name=self.task_name,
                band_name=self.band_name,
                chosen_mark=self.chosen_mark,
            )
        )


class BandWidget(Grid):
    DEFAULT_CLASSES = "band"

    def __init__(self, rubric, task_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rubric: Rubric = rubric
        self.task_name: str = task_name
        self.task_obj: Task = self.rubric.tasks[self.task_name]

    def compose(self) -> ComposeResult:
        cols = self.task_obj.max_marks() + 1 - (self.task_obj.min_marks() or 0)
        self.styles.grid_size_columns = cols + 4
        grid_columns = " 1fr" * (cols + 4)
        grid_rows = "1" + " auto" * (len(self.task_obj.bands))
        self.styles.grid_columns = f"4 auto auto auto {grid_columns}"
        self.styles.grid_rows = grid_rows

        # Input for total marks
        yield Label(
            str(self.task_obj.calc_marks()),
            classes="mark",
        )

        # Show the max possible mark
        yield Static("/", classes="mark")
        yield Static(f"{self.task_obj.max_marks()}", classes="mark")
        yield Static(" ", classes="whitespace")

        # The first row of requirement labels
        headings = self.task_obj.headings
        for marks, name in headings.items():
            yield Static(f"{name} ({marks})")

        # aaaand sub-bands
        for key, band in self.task_obj.bands.items():
            yield Static(f"{key}", classes="subband_label")
            yield Static("", classes="whitespace")

            # Then create MarkButtons for each item in the subband
            # (remembering only to iterate the )
            for mark, name in [
                item
                for item in headings.items()
                if self.task_obj.max_marks() >= item[0]
                and (self.task_obj.min_marks() or 0) <= item[0]
            ]:
                btn = MarkButton(
                    label=band.descriptions[mark],
                    task_name=self.task_name,
                    band_name=key,
                    chosen_mark=mark,
                    classes="marktile",
                )
                yield btn

    def on_mark_selected(self, message: MarkSelected) -> None:
        print(message)
        if message.task_name != self.task_name:
            return  # Not for us; ignore.

        # Unhighlight any MarkButton in the same subband
        for btn in self.query(MarkButton):
            if btn.band_name == message.band_name:
                btn.remove_class("selected_markbutton")

        # Highlight the clicked one
        for btn in self.query(MarkButton):
            if (
                btn.band_name == message.band_name
                and btn.chosen_mark == message.chosen_mark
            ):
                btn.add_class("selected_markbutton")

    def update_band_display(self) -> None:
        self.query_one(Label).update(
            repr(self.rubric.tasks[self.task_name].calc_marks())
        )


class TaskPanel(Collapsible):
    """
    A collapsible panel for each task. Displays the task's description, comment,
    and one BandWidget for each band in the task.
    """

    def __init__(self, rubric, task_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rubric = rubric
        self.task_name = task_name
        self.title = f"Task: {self.task_name}"

    def compose(self) -> ComposeResult:
        task = self.rubric.tasks[self.task_name]

        # Description
        if task.description:
            yield Static(f"Description: {task.description}")

        # Comment
        yield Static(f"Comment: {task.comment}")

        # Create a BandWidget for each band
        yield BandWidget(self.rubric, self.task_name)


class MarkPanel(VerticalScroll):
    """
    Displays all tasks in the rubric (via TaskPanels) and updates the border
    to show total marks as they change.
    """

    def __init__(self, rubric, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rubric = rubric

    def compose(self) -> ComposeResult:
        """
        If rubric has tasks, create a TaskPanel for each.
        Otherwise, indicate no tasks found.
        """
        if not self.rubric or not self.rubric.tasks:
            self.border_title = "No Criteria"
            yield Static("No tasks found in this rubric.")
            return

        self.update_border()
        for task_name in self.rubric.tasks:
            yield TaskPanel(self.rubric, task_name)

    def update_border(self) -> None:
        """
        Updates the border title to show the current marks / max marks.
        """
        current_marks = self.rubric.calc_marks()
        max_marks = self.rubric.max_marks()
        if max_marks > 0:
            percent = (current_marks / max_marks) * 100
            self.border_title = (
                f"Marks: {current_marks:.1f}/{max_marks} ({percent:.1f}%)"
            )
        else:
            self.border_title = "Marks: 0/0"

    def on_mark_selected(self, event: MarkSelected) -> None:
        """
        When a MarkButton is clicked, update the rubric model and refresh.
        """
        # Update the rubric with the chosen mark
        self.rubric.update_mark(event.task_name, event.band_name, event.chosen_mark)

        # Recalculate the total marks in the border
        self.update_border()

        for bandwidget in self.query(BandWidget):
            if bandwidget.task_name == event.task_name:
                bandwidget.update_band_display()
