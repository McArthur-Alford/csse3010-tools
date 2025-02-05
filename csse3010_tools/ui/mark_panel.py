from typing import Optional, List

from textual import on
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


class TaskPanel(Container):
    def __init__(self, rubric: Rubric, task_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rubric = rubric
        self.task_name = task_name
        self.task_obj: Task = self.rubric.tasks[self.task_name]

    def compose(self) -> ComposeResult:
        # Build a collapsible (same "Task: ..." title as before)
        with Collapsible(title=f"Task"):
            # Description
            if self.task_obj.description:
                yield (Static(f"{self.task_obj.description}"))

            # Create a grid that acts like the old BandWidget
            band_grid = Grid(classes="band")
            with band_grid:
                # Same layout logic
                cols = self.task_obj.max_marks() + 1 - (self.task_obj.min_marks() or 0)
                band_grid.styles.grid_size_columns = cols + 1
                grid_columns = "4" + " 1fr" * (cols)
                grid_rows = "1" + " auto" * (len(self.task_obj.bands))
                band_grid.styles.grid_columns = f"{grid_columns}"
                band_grid.styles.grid_rows = grid_rows

                yield Static("CID")

                # Heading row
                headings = self.task_obj.headings
                for marks, name in headings.items():
                    yield (Static(f"{name} ({marks})"))

                # Sub-bands
                for key, band in self.task_obj.bands.items():
                    yield (Static(f"{key}", classes="subband_label"))
                    # yield (Static("", classes="whitespace"))

                    # Create a MarkButton for each heading item
                    for mark, _ in [
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
                        yield (btn)
            # Comment
            yield Input(
                value=f"{self.task_obj.comment}",
                placeholder="Comment",
                classes="comment_input",
            )

    @on(Input.Changed, ".comment_input")
    def on_input_changed(self, message: Input.Changed) -> None:
        self.rubric.update_comment(self.task_name, message.value)

    def on_mount(self):
        self.refresh_calculation()

    def on_mark_selected(self, message: MarkSelected) -> None:
        """When a MarkButton is clicked, highlight it and unhighlight others in the same sub-band."""
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

    def refresh_calculation(self) -> None:
        """Refresh the label that shows the total mark for this task."""
        collapsible = self.query_one("Collapsible", Collapsible)
        collapsible.title = f"({self.task_obj.calc_marks()}/{self.task_obj.max_marks()}) Task: {self.task_name}"


class MarkPanel(VerticalScroll):
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

        # Update the display for the relevant task
        for panel in self.query(TaskPanel):
            if panel.task_name == event.task_name:
                panel.refresh_calculation()
