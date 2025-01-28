from typing import Optional

from textual.app import ComposeResult
from textual.containers import Grid, VerticalScroll, Container
from textual.message import Message
from textual.widgets import Button, Collapsible, Input, Placeholder, Static

from csse3010_tools.criteria import rubric_to_markdown_table

class MarkSelected(Message):
    """Message indicating a mark button has been selected."""

    def __init__(
        self, 
        task_index: int, 
        band_index: int, 
        subband: int, 
        mark: int
    ) -> None:
        super().__init__()
        self.task_index = task_index
        self.band_index = band_index
        self.subband = subband
        self.mark  = mark

class MarkButton(Button):
    def __init__(
        self,
        label: str,
        task_index: int,
        band_index: int,
        subband: int,
        mark: int,
        *args,
        **kwargs
    ):
        super().__init__(label, *args, **kwargs)
        self.task_index = task_index
        self.band_index = band_index
        self.subband  = subband
        self.mark = mark

    def on_click(self) -> None:
        self.post_message(
            MarkSelected(
                self.task_index,
                self.band_index,
                self.subband,
                self.mark
            )
        )


class BandWidget(Grid):
    DEFAULT_CLASSES = "band"

    def __init__(
        self,
        rubric,
        task_index: int,
        band_index: int,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.rubric = rubric
        self.task_index = task_index
        self.band_index = band_index

        self.band = self.rubric.tasks[self.task_index].bands[self.band_index]

        self.mark_input: Optional[Input] = None
        self._mark_buttons: list[MarkButton] = []

        self.id = f"band_{band_index}"

    def compose(self) -> ComposeResult:
        cols = self.band.max_marks() - self.band.min_marks() + 1
        self.styles.grid_size_columns = cols + 4
        # grid_columns = "5 5 5 5" + " 1fr" * cols
        grid_columns = " 1fr" * (cols + 4)
        grid_rows = "1" + " auto" * (len(self.band.requirements))
        self.styles.grid_columns = f"4 auto auto auto {grid_columns}"
        self.styles.grid_rows = grid_rows

        # Input for total marks
        self.mark_input = Input(
            value=str(self.band.calculate()),
            placeholder="00",
            max_length=2,
            classes="mark",
            id="mark_input"
        )
        yield self.mark_input

        # Show the max possible mark
        yield Static("/", classes="mark")
        yield Static(f"{self.band.max_marks()}", classes="mark")
        yield Static(" ", classes="whitespace")

        # The first row of requirement labels
        headings = self.band.headings()
        for marks, name in headings.items():
            yield Static(f"{name} ({marks})")

        # aaaand sub-bands
        for key in self.band.requirements:
            requirements = self.band.requirements[key]
            yield Static(
                f"{key}",
                classes="subband_label"
            )
            yield Static("", classes="whitespace")

            # Then create MarkButtons for each item in the subband
            for mark, name in headings.items():
                req = requirements.get(mark)

                if req is not None:
                    label = "<===" if req.defers == "up" else (
                        "===>" if req.defers == "down" else req.description
                    )

                #     if req.defers is not None:
                #         yield Static(label, classes="marktile")
                #         continue
                # else:
                #     label = "-"
                #     yield Static(label, classes="marktile")
                #     continue

                btn = MarkButton(
                    label=label,
                    task_index=self.task_index,
                    band_index=self.band_index,
                    subband=key,
                    mark=mark,
                    classes="marktile"
                )
                self._mark_buttons.append(btn)
                yield btn

    def on_mark_selected(self, message: MarkSelected) -> None:
        if message.band_index != self.band_index or message.task_index != self.task_index:
            return  # Not for us; ignore.

        # Unhighlight any MarkButton in the same subband
        for btn in self._mark_buttons:
            if btn.subband == message.subband:
                btn.remove_class("selected_markbutton")

        # Highlight the clicked one
        for btn in self._mark_buttons:
            if (
                btn.subband  == message.subband
                and btn.mark == message.mark
            ):
                btn.add_class("selected_markbutton")

    def update_band_display(self) -> None:
        self.band = self.rubric.tasks[self.task_index].bands[self.band_index]
        if self.mark_input:
            self.mark_input.value = str(self.band.calculate())


class TaskPanel(Collapsible):
    DEFAULT_CLASSES = "task_collapsible"

    def __init__(self, rubric, task_index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rubric = rubric
        self.task_index = task_index

    def compose(self) -> ComposeResult:
        yield self._title
        with self.Contents(*self._contents_list):
            task = self.rubric.tasks[self.task_index]
            for j, band in enumerate(task.bands):
                yield BandWidget(self.rubric, self.task_index, j)

            # If there's a description for the task, show it
            if task.description is not None:
                yield Static(f"{task.description}", classes="taskdescription")
            else:
                # yield Static("", classes="taskdescription")
                pass

class MarkPanel(VerticalScroll):
    DEFAULT_CLASSES = "panel"

    def __init__(self, rubric, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rubric = rubric

    def compose(self) -> ComposeResult:
        if not self.rubric or not self.rubric.tasks:
            self.border_title = "No Criteria"
            yield Static("Unable to load criteria, is year/semester/stage valid?")
            return

        self.update_border()

        for i, task in enumerate(self.rubric.tasks):
            yield TaskPanel(
                self.rubric, 
                i, 
                title=f"Task: {task.name}",
                id=f"task_panel_{i}",
            )

    def update_border(self) -> None:
        # self.border_title = (
        #     f"Criteria: {self.rubric.year} / "
        #     f"Sem: {self.rubric.semester} / Stage: {self.rubric.stage}"
        # )

        marks = self.rubric.marks()
        max_marks = self.rubric.max_marks()
        percent = "{:.2f}".format((marks / float(max_marks) * 100))

        self.border_title = f"total marks: {marks}/{max_marks} ({percent}%)"

    def on_mark_selected(self, message: MarkSelected) -> None:
        # Update the rubric model
        self.rubric.update(
            task=message.task_index,
            band=message.band_index,
            subband=message.subband,
            mark=message.mark
        )
        print(
            f"""
                task: {message.task_index}
                band: {message.band_index}
                subband: {message.subband}
                mark: {message.mark}
            """
        )

        self.update_border()

        band_widget = self.query_one(
            f"#task_panel_{message.task_index} #band_{message.band_index}",
            expect_type=BandWidget
        )
        band_widget.update_band_display()
