from textual.widgets import Label, Select
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.message import Message
from textual.suggester import SuggestFromList
from textual.validation import Regex, ValidationResult
from textual import on


class CommitHashSelect(Horizontal):
    """A label + dropdown for commit hashes."""
    DEFAULT_CLASSES = "metadata_field"
   
    class Updated(Message):
        """Fires when the user selects a new commit hash."""
        def __init__(self, commit_hash: str) -> None:
            self.commit_hash = commit_hash
            super().__init__()

    def compose(self) -> ComposeResult:
        with Horizontal(classes="metadata_field"):
            yield Label("Commit Hash:")
            yield Select([], id="commit-hash-dropdown", allow_blank=True)

    @on(Select.Changed)
    def commit_changed(self, event: Select.Changed) -> None:
        """Send an Updated message with the newly selected commit."""
        if event.value:
            self.post_message(self.Updated(str(event.value)))


