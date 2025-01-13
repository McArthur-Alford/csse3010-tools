from textual.containers import Container, Horizontal
from textual.widgets import Input
from csse3010_tools.ui.student_select import StudentSelect
from csse3010_tools.ui.commit_hash_select import CommitHashSelect

class GitSelect(Container):
    """
       A panel to hold all of the related fields to selecting a git repo/hash and student
    """

    DEFAULT_CLASSES="panel"

    def compose(self):
        yield StudentSelect()
        yield CommitHashSelect()
        with Horizontal(classes="metadata_field"):
            yield Input(placeholder="Student Name", disabled=True)
        self.border_title = "Select Student"
