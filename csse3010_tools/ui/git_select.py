from textual.containers import Container, Horizontal
from textual.widgets import Input
from csse3010_tools.ui.student_select import StudentNumber
from csse3010_tools.ui.commit_hash_select import CommitHashSelect


class GitSelect(Container):
    """
    A panel to hold all of the related fields to selecting a git repo/hash and student
    """

    def compose(self):
        with Horizontal():
            yield StudentNumber()
            yield CommitHashSelect()
        yield Input(placeholder="Student Name", disabled=True, id="StudentName")
        self.border_title = "Select Student"
