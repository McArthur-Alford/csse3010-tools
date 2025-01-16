from textual import on
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Select, Static

from csse3010_tools.appstate import AppState
from csse3010_tools.criteria import Criteria, example_criteria
from csse3010_tools.ui.banner import Banner
from csse3010_tools.ui.commit_hash_select import CommitHashSelect
from csse3010_tools.ui.criteria_select import CriteriaSelect
from csse3010_tools.ui.git_select import GitSelect
from csse3010_tools.ui.student_select import StudentNumber
from csse3010_tools.ui.mark_panel import MarkPanel

class LeftPanel(VerticalScroll):
    def compose(self) -> ComposeResult:
        self.border_title = "Configuration"
        yield CriteriaSelect()
        yield GitSelect()

class Body(HorizontalScroll):
    def compose(self) -> ComposeResult:
        yield LeftPanel()
        with Vertical(id="right_panel"):
            yield MarkPanel(None)

class MarkingApp(App):
    CSS_PATH = "style.tcss"
    TITLE = "CSSE3010 Tools"
    SUB_TITLE = "Marking"

    app_state: AppState = AppState()
    active_student: reactive[str] = reactive("")
    active_commit: reactive[str] = reactive("")
    current_criteria: reactive[Criteria | None] = reactive(None)

    def watch_app_state(self) -> None:
        """Called whenever app_state is mutated (if we call self.mutate_reactive)."""
        print("App State changed")

    def watch_active_student(self, old: str, new: str) -> None:
        """When the user picks a new student, we can refresh the commit hash dropdown's choices."""
        if old == new:
            return
        print(f"Active student changed from {old} to {new}")
        commit_hash_dropdown = self.query_one("#commit-hash-dropdown", Select)
        commits = [("abcdefg", "abcdefg"), ("1234567", "1234567")]
        commit_hash_dropdown.set_options(commits)
        commit_hash_dropdown.clear()

    @on(StudentNumber.Updated)
    def on_student_number_updated(self, message: StudentNumber.Updated) -> None:
        """User selected a valid student number."""
        self.active_student = message.number

    @on(CommitHashSelect.Updated)
    def on_commit_hash_updated(self, message: CommitHashSelect.Updated) -> None:
        """User selected a commit hash from the dropdown."""
        self.active_commit = message.commit_hash
        print(f"User selected commit: {self.active_commit}")
        # TODO self.app_state.set_active_commit(...)

    @on(CriteriaSelect.Picked)
    def on_criteria_picked(self, message: CriteriaSelect.Picked) -> None:
        """User changed year/semester/stage in the criteria picker."""
        year, sem, stage = message.year, message.semester, message.stage
        print(f"Criteria chosen: year={year}, semester={sem}, stage={stage}")

        try:
            self.current_criteria = self.app_state.criteria(year, sem, stage)
        except FileNotFoundError:
            # You might want to handle this more gracefully
            print(f"No criteria file found for {year}/{sem}/{stage}")
            self.current_criteria = None

        self.build_criteria_panel()

    def build_criteria_panel(self) -> None:
        """
        Clears the MarkPanel and populates it based on the current_criteria.
        """
        right_panel = self.query_one("#right_panel")
        right_panel.remove_children()

        new_mark_panel = MarkPanel(self.current_criteria)
        right_panel.mount(new_mark_panel)

    def on_mount(self) -> None:
        banner = self.query_one(Banner)
        banner.version = f"Marking Tools V1"
        banner.user = f"Gitea User: {self.app_state.user}"

        # Bind the list of student numbers to the StudentNumber widget
        student_number: StudentNumber = self.query_one(StudentNumber)
        student_number.data_bind(student_numbers=self.app_state.student_numbers)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Vertical():
            yield Banner()
            yield Body()


def main():
    app = MarkingApp()
    app.run()

if __name__ == "__main__":
    main()
