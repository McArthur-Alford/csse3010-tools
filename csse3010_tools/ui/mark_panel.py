from typing import Optional
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Grid
from textual.widgets import Button, Collapsible, Input, Static
from textual.message import Message

class MarkButton(Button):
    DEFAULT_CLASSES = "markbutton"
    subband: int
    index: int

    class Selected(Message):
        task: Optional[int]
        band: Optional[int]
        subband: int
        index: int

        def __init__(self, subband: int, index: int) -> None:
            self.task = None
            self.band = None
            self.subband = subband
            self.index = index
            super().__init__()

    def __init__(self, subband, index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subband = subband
        self.index = index

    def on_click(self) -> None:
        self.post_message(self.Selected(self.subband, self.index))

class BandWidget(Grid):
    DEFAULT_CLASSES = "band"
    band_index: int

    def __init__(self, band, band_index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.band = band
        self.band_index = band_index
        self.id = f"band_{band_index}"

    def on_mark_button_selected(self, message: MarkButton.Selected) -> None:
        message.band = self.band_index

        # set the class of the active button to keep it highlighted?
        buttons = self.query_children(MarkButton)
        for button in buttons:
            if button.subband == message.subband:
                button.remove_class("selected_markbutton")
            if button.subband != message.subband or button.index != message.index:
                continue
            button.add_class("selected_markbutton")

    def reband(self, band):
        self.band = band
        self.query_one("#mark_input", Input).value = f"{self.band.calculate()}"

    def compose(self) -> ComposeResult:
        self.styles.grid_size_rows = len(self.band.requirements) + 1
        self.styles.grid_size_columns = len(self.band.requirements[0]) + 4
        grid_columns = "1fr " * len(self.band.requirements[0])
        self.styles.grid_columns = f"4 auto auto auto {grid_columns}"
        # self.styles.grid_rows = "1" + (" auto" * (len(self.band.requirements)))
        yield Input(value=f"{self.band.calculate()}", placeholder="00", max_length = 2, classes="mark", id="mark_input")
        yield Static("/", classes="mark")
        yield Static(f"{self.band.max_marks()}", classes="mark")
        yield Static(" ", classes="whitespace")
        for req in self.band.requirements[0]:
            yield Static(f"{req.name} ({req.marks})")

        for i, requirements in enumerate(self.band.requirements):
            x = Static(f"{self.band.keys[i] if i < len(self.band.keys) else ""}", classes="subband_label")
            yield x
            yield Static("")
            for j, req in enumerate(requirements):
                if req.defers:
                    if req.defers == "up":
                        yield MarkButton(i, j, "<--")
                    else:
                        yield MarkButton(i, j, "-->")
                else:
                    yield MarkButton(i, j, f"{req.description}")

class TaskPanel(Collapsible):
    DEFAULT_CLASSES = "task_collapsible"
    task_index: int
    
    def __init__(self, task_index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_index = task_index

    def on_mark_button_selected(self, message: MarkButton.Selected) -> None:
        message.task = self.task_index

class MarkPanel(VerticalScroll):
    DEFAULT_CLASSES = "panel"

    def __init__(self, rubric, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rubric = rubric

    def on_mark_button_selected(self, message: MarkButton.Selected) -> None:
        # Calculate the task mark and set the task total
        self.rubric.update(message.task, message.band, message.subband, message.index)
        self.query_one(f"#task_panel_{message.task}", TaskPanel) \
            .query_one(f"#band_{message.band}", BandWidget) \
            .reband(self.rubric.tasks[message.task].bands[message.band])

    def compose(self) -> ComposeResult:
        self.border_title = "No Criteria"

        if not self.rubric or not self.rubric.tasks:
            yield Static("Unable to load criteria, is year/semester/stage valid?")
            return

        self.border_title = (
            f"Criteria: {self.rubric.year} / "
            f"Sem: {self.rubric.semester} / Stage: {self.rubric.stage}"
        )

        self.border_subtitle = "total marks: 6/10 (60%)"

        for i, task in enumerate(self.rubric.tasks):
            with TaskPanel(i, title=f"Task: {task.name}", id=f"task_panel_{i}"):
                for j, band in enumerate(task.bands):
                    yield BandWidget(band, j)
                if task.description is not None:
                    yield Static(f"{task.description}", classes="taskdescription")
                else:
                    yield Static("", classes="taskdescription")
