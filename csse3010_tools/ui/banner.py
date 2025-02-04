from textual.widgets import Label
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.app import ComposeResult


class Banner(Horizontal):
    """Displays some info from Gitea (like version & user)."""

    version = reactive("gitea version")
    user = reactive("gitea user")

    def watch_version(self, old_version: str, new_version: str) -> None:
        self.query_one("#gitea_version", Label).update(str(new_version))

    def watch_user(self, old_user: str, new_user: str) -> None:
        self.query_one("#gitea_user", Label).update(str(new_user))

    def compose(self) -> ComposeResult:
        yield Label("GITEA VERSION", id="gitea_version")
        yield Label("GITEA USER", id="gitea_user")
