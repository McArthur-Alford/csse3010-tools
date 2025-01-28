from textual.containers import Container
from textual.widgets import Button

class BuildMenu(Container):
    # DEFAULT_CLASSES="panel"

    def compose(self):
        self.border_title = "Build Menu"
        yield Button("Build", classes="metadata_field")
        yield Button("Run", classes="metadata_field")
        yield Button("Clone", classes="metadata_field")

