from textual.widgets import Button, Label
from textual.app import ComposeResult
from textual.containers import Horizontal


class SaveMenu(Horizontal):
    def compose(self) -> ComposeResult:
        yield Button(
            "Load",
            id="load_button",
            tooltip="Load the marks from the .md file, done automatically when the student is first selected",
        )
        yield Button("Save", id="save_button", tooltip="Save the marks to the .md file")
        yield Label("No Student Selected", id="save_label")
        # Label changes to:
        # - disabled if .md and current rubric match
        # - enabled, ".md file is out of date or changed" otherwise
