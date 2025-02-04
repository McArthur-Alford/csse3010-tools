from typing import Optional

from textual.app import ComposeResult
from textual.containers import Grid, VerticalScroll, Container
from textual.message import Message
from textual.widgets import Button, Collapsible, Input, Placeholder, Static, TextArea
from textual.widget import Widget

from csse3010_tools.criteria import rubric_to_markdown_table

class MarkPanelRaw(TextArea):
    def on_mount(self):
        self.language = "markdown"
        pass

    # def compose(self) -> ComposeResult:
    #     # yield TextArea.code_editor("", language="markdown")
    #     yield TextArea()
