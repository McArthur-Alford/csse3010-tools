from textual.containers import Container, Horizontal
from textual.widgets import Button, Log
from textual.messages import Message
from dataclasses import dataclass


@dataclass
class BuildCommand(Message):
    type: str

class BuildMenu(Container):
    def compose(self):
        with Horizontal(id="buildbar"):
            yield Button("Build", id="buildbutton", classes="metadata_field")
            yield Button("flash", id="flashbutton", classes="metadata_field")
            yield Button("Clean", id="cleanbutton", classes="metadata_field")
        yield Log(id="buildlog")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "buildbutton":
            self.post_message(BuildCommand("build"))
        if event.button.id == "flashbutton":
            self.post_message(BuildCommand("flash"))
        if event.button.id == "cleanbutton":
            self.post_message(BuildCommand("clean"))
