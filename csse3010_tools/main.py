from typing import Optional

from textual import on
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll, Vertical, VerticalScroll, Container
from textual.events import Resize
from textual.reactive import reactive
from textual.widgets import Footer, Header, Select, TabbedContent, TabPane, Log

from csse3010_tools.appstate import AppState
from csse3010_tools.criteria import Rubric, rubric_to_markdown_table
from csse3010_tools.ui.banner import Banner
from csse3010_tools.ui.build_menu import BuildMenu
from csse3010_tools.ui.commit_hash_select import CommitHashSelect
from csse3010_tools.ui.criteria_select import CriteriaSelect
from csse3010_tools.ui.git_select import GitSelect
from csse3010_tools.ui.mark_panel import MarkPanel, MarkSelected
from csse3010_tools.ui.student_select import StudentNumber


class Body(Container):
    def compose(self) -> ComposeResult:
        yield GitSelect()
        with TabbedContent(initial="marking"):
            with TabPane("Marking", id="marking"):
                with Vertical(id="Config"):
                    yield CriteriaSelect()
                with Vertical(id="mark_panel"):
                    yield MarkPanel(None)
        yield Log()

class MarkingApp(App):
    CSS_PATH = "style.tcss"
    TITLE = "CSSE3010 Tools"
    SUB_TITLE = "Marking"

    BINDINGS = [
        ("ctrl+s", "select_student", "Select Student"),
        ("ctrl+b", "build", "Build"),
        ("ctrl+d", "deploy", "Deploy"),
        ("ctrl+c", "clean", "Clean"),
        ("ctrl+r", "reset", "Reset")
    ]

    app_state: AppState = AppState()
    active_student: reactive[str] = reactive("")
    active_commit: reactive[Optional[str]] = reactive(None)
    current_criteria: reactive[Rubric | None] = reactive(None)

    @on(MarkSelected)
    def on_mark_selected(self, _message: MarkSelected) -> None:
        if self.current_criteria is None:
            return

        print(rubric_to_markdown_table(self.current_criteria))

    def watch_app_state(self) -> None:
        """Called whenever app_state is mutated (if we call self.mutate_reactive)."""
        print("App State changed")

    def watch_active_student(self, old: str, new: str) -> None:
        """When the user picks a new student, we can refresh the commit hash dropdown's choices."""
        if old == new:
            return
        print(f"Active student changed from {old} to {new}")
        commit_hash_dropdown = self.query_one("#commit-hash-dropdown", Select)
        commits = self.app_state.commits(self.active_student)
        commit_hash_dropdown.set_options([(f"{commit.hash[:16]}\n{commit.date}", commit.hash) for commit in commits])
        commit_hash_dropdown.clear()

    @on(StudentNumber.Updated)
    def on_student_number_updated(self, message: StudentNumber.Updated) -> None:
        """User selected a valid student number."""
        self.active_student = message.number
        self.active_commit = None
        self.app_state.clone_repo(self.active_student)

    @on(CommitHashSelect.Updated)
    def on_commit_hash_updated(self, message: CommitHashSelect.Updated) -> None:
        """User selected a commit hash from the dropdown."""
        self.active_commit = message.commit_hash
        print(f"User selected commit: {self.active_commit}")
        # Set the tooltip for the commit box to be the commit message
        commits = self.app_state.commits(self.active_student)
        commits = [commit for commit in commits if commit.hash == message.commit_hash]
        commit_hash_dropdown = self.query_one("#commit-hash-dropdown", Select)
        if len(commits) == 0:
            commit_hash_dropdown.tooltip = ""
            self.active_commit = None
            return
        commit = commits[0]
        commit_hash_dropdown.tooltip = commit.message
        self.active_commit = commit.hash

        self.app_state.clone_repo(self.active_student, self.active_commit)

    @on(CriteriaSelect.Picked)
    def on_criteria_picked(self, message: CriteriaSelect.Picked) -> None:
        """User changed year/semester/stage in the criteria picker."""
        year, sem, stage = message.year, message.semester, message.stage
        print(f"Criteria chosen: year={year}, semester={sem}, stage={stage}")

        try:
            self.current_criteria = self.app_state.criteria(year, sem, stage)
        except FileNotFoundError:
            print(f"No criteria file found for {year}/{sem}/{stage}")
            self.current_criteria = None

        self.build_criteria_panel()

    def build_criteria_panel(self) -> None:
        """
        Clears the MarkPanel and populates it based on the current_criteria.
        """
        mark_panels = self.query("#mark_panel")
        for mark_panel in mark_panels:
            mark_panel.remove_children()

            new_mark_panel = MarkPanel(self.current_criteria)
            mark_panel.mount(new_mark_panel)

    def on_mount(self) -> None:
        banner = self.query_one(Banner)
        banner.version = "Marking Tools V1"
        banner.user = f"Gitea User: {self.app_state.user}"
        self.theme = "tokyo-night"

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
