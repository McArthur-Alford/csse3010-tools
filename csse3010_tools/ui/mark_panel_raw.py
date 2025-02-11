from textual.widgets import TextArea


class MarkPanelRaw(TextArea):
    def on_mount(self):
        self.language = "markdown"
        pass
