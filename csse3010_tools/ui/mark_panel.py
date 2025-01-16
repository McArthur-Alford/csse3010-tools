from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Input, Label, Static

class BandWidget(Horizontal):
    DEFAULT_CLASSES = "band"

    def __init__(self, band_data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.band_data = band_data

    def compose(self) -> ComposeResult:
        with Horizontal(classes="mark_container"):
            yield Input(classes="mark", placeholder="00")
            yield Label(f"/ {len(self.band_data.criteria):02d}")

        yield Label(self.band_data.band_name)

        # Grade buttons (TODO pull from the settings?)
        grade_labels = ["Exemplary", "Proficient", "Competent", "Insufficient", "Absent"]
        with Horizontal(classes="grade_grid"):
            for grade_label in grade_labels:
                yield Button(grade_label, classes="grade_button")


class MarkPanel(VerticalScroll):
    DEFAULT_CLASSES = "panel"

    def __init__(self, criteria_data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.criteria_data = criteria_data

    def compose(self) -> ComposeResult:
        self.border_title = "No Criteria"

        if not self.criteria_data or not self.criteria_data.tasks:
            yield Static("Unable to load criteria, is year/semester/stage valid?")
            return

        # Example: Put a border title with year/semester/stage
        self.border_title = (
            f"Criteria: {self.criteria_data.year} / "
            f"Sem: {self.criteria_data.semester} / Stage: {self.criteria_data.stage}"
        )

        for task in self.criteria_data.tasks:
            # Show a heading for the task
            yield Static(f"Task: {task.task_name}", classes="task_title")

            # Possibly also show the 'task.description' if relevant
            if task.description.strip():
                yield Static(f"Description: {task.description}", classes="task_description")

            # For each category in this task
            for category in task.categories:
                # Category heading
                yield Static(f"Category: {category.category_id}", classes="category_title")

                # For each band in this category, yield a BandWidget
                for band in category.bands:
                    yield BandWidget(band)
