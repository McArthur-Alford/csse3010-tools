from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll, Vertical, VerticalScroll, Container
from textual.events import Resize
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    Select,
    TabbedContent,
    TabPane,
    Log,
    Input,
    Button,
    Label,
)

from csse3010_tools.appstate import AppState
from csse3010_tools.ui.banner import Banner
from csse3010_tools.ui.build_menu import BuildMenu
from csse3010_tools.ui.commit_hash_select import CommitHashSelect
from csse3010_tools.ui.criteria_select import CriteriaSelect
from csse3010_tools.ui.git_select import GitSelect
from csse3010_tools.ui.mark_panel import MarkPanel, MarkSelected, CommentInput
from csse3010_tools.ui.student_select import StudentNumber
from csse3010_tools.ui.mark_panel_raw import MarkPanelRaw
from csse3010_tools.ui.saveload import SaveMenu
from csse3010_tools.rubric import Rubric


class Body(Container):
    def compose(self) -> ComposeResult:
        yield GitSelect()
        yield CriteriaSelect()
        with TabbedContent(initial="marking", disabled=True):
            with TabPane("Marking", id="marking"):
                yield SaveMenu()
                with Vertical(id="mark_panel"):
                    # yield MarkPanel(None)
                    yield Label("Xnopyt")
            with TabPane("Marking Output Preview", id="markingraw"):
                yield MarkPanelRaw()
            with TabPane("Build/Run", id="buildmenu"):
                yield Log()
            with TabPane("Code Viewer", id="viewer"):
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
        ("ctrl+r", "reset", "Reset"),
    ]

    # Use the new AppState
    app_state: AppState = AppState()

    # Reactives for our UI
    active_student: reactive[str] = reactive("")
    active_commit: reactive[Optional[str]] = reactive(None)
    current_criteria: reactive[Rubric | None] = reactive(None)
    marks_changed: reactive[bool] = reactive(False)
    active_stage: reactive[str] = reactive("")

    def write_marks(self) -> None:
        """Write the current criteria to the marks.md file for the active student and stage."""
        if self.current_criteria is None or self.active_student == "":
            print("Unable to write file (no active student or criteria).")
            return
        self.app_state.write_marks(
            self.current_criteria, self.active_student, self.active_stage
        )

    def load_marks(self) -> None:
        """Load any existing marks from the marks.md file into the current_criteria."""
        if self.current_criteria is None or self.active_student == "":
            print("Unable to load file (no active student or criteria).")
            return
        md = self.app_state.read_marks(self.active_student, self.active_stage)
        self.current_criteria.load_md(md)
        self.build_criteria_panel()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Respond to button presses."""
        if event.button.id == "save_button":
            print("Saving")
            self.write_marks()
        if event.button.id == "load_button":
            print("Loading")
            self.load_marks()

    @on(CommentInput.CommentChanged)
    def on_comment_changed(self, _message: CommentInput.CommentChanged) -> None:
        """Update the preview pane and save marks when a comment changes."""
        if self.current_criteria is None:
            return

        markpanel = self.query_one(MarkPanelRaw)
        markpanel.text = self.current_criteria.into_md()
        self.write_marks()

    @on(MarkSelected)
    def on_mark_selected(self, _message: MarkSelected) -> None:
        """Update the preview pane and write marks when a rubric selection changes."""
        if self.current_criteria is None or _message is None:
            return

        markpanel = self.query_one(MarkPanelRaw)
        markpanel.text = self.current_criteria.into_md()
        print(_message)
        self.write_marks()

    def watch_active_student(self, old: str, new: str) -> None:
        """When the user picks a new student, repopulate the commit hash dropdown."""
        if old == new or new == "":
            return
        print(f"Active student changed from {old} to {new}")

        # Get the commits for the newly selected student
        commits = self.app_state.list_commits(self.active_student)

        # Update the commit dropdown
        commit_hash_dropdown = self.query_one("#commit-hash-dropdown", Select)
        commit_hash_dropdown.clear()
        commit_hash_dropdown.set_options(
            [(f"{commit.hash[:16]}\n{commit.date}", commit.hash) for commit in commits]
        )

    @on(StudentNumber.Updated)
    async def on_student_number_updated(self, message: StudentNumber.Updated) -> None:
        """User selected a student number from the StudentNumber widget."""
        if message.valid:
            self.active_commit = None
            self.active_student = message.number

            # Tell our AppState about the new student
            self.app_state.student_number = message.number

            # Update the UI
            student_name = self.query_one("#StudentName", Input)
            student = self.app_state.get_student_name(message.number)
            student_name.value = student if student else "Unknown"
            self.query_one(TabbedContent).disabled = False

            # Load the student's marks (if any)
            self.load_marks()

            self.query_one("#save_label", Label).update(f"Marking {message.number}")
        else:
            self.active_student = ""
            self.active_commit = None
            self.query_one(TabbedContent).disabled = True
            self.query_one("#save_label", Label).update("No Student Selected")

    @on(CommitHashSelect.Updated)
    async def on_commit_hash_updated(self, message: CommitHashSelect.Updated) -> None:
        """User selected a commit hash from the dropdown."""
        self.active_commit = message.commit_hash
        if self.active_student == "":
            return

        # If no commit hash, disable build menu. Otherwise, enable.
        build_menu = self.query_one("#buildmenu")
        build_menu.disabled = message.commit_hash == ""

        print(f"User selected commit: {self.active_commit}")

        # Update tooltip with commit message
        commits = self.app_state.list_commits(self.active_student)
        matching = [commit for commit in commits if commit.hash == message.commit_hash]
        commit_hash_dropdown = self.query_one("#commit-hash-dropdown", Select)
        if not matching:
            commit_hash_dropdown.tooltip = ""
            self.active_commit = None
            return

        commit = matching[0]
        commit_hash_dropdown.tooltip = commit.message
        self.active_commit = commit.hash

        # Tell the AppState to switch to this commit
        self.app_state.commit_hash = self.active_commit

    @on(CriteriaSelect.Picked)
    def on_criteria_picked(self, message: CriteriaSelect.Picked) -> None:
        """User changed year/semester/stage in the criteria picker."""
        year, sem, stage = message.year, message.semester, message.stage
        print(f"Criteria chosen: year={year}, semester={sem}, stage={stage}")

        # Update our AppState to clone the correct marks repo
        self.app_state.year = year
        self.app_state.semester = sem
        self.app_state.stage = stage

        # Attempt to load the matching rubric
        try:
            self.current_criteria = self.app_state.get_criteria(year, sem, stage)
        except FileNotFoundError:
            print(f"No criteria file found for {year}/{sem}/{stage}")
            self.current_criteria = None

        self.active_stage = stage
        self.build_criteria_panel()
        self.load_marks()

    def build_criteria_panel(self) -> None:
        """
        Clears the MarkPanel container and populates it with the current_criteria.
        """
        mark_panels = self.query("#mark_panel")
        for mark_panel in mark_panels:
            mark_panel.remove_children()
            if self.current_criteria:
                new_mark_panel = MarkPanel(self.current_criteria)
                mark_panel.mount(new_mark_panel)

    def on_mount(self) -> None:
        """Initialize the UI when the app is mounted."""
        banner = self.query_one(Banner)
        banner.version = "Marking Tools V1"
        banner.user = f"Gitea User: {self.app_state._gitea.get_user().username}"
        self.theme = "tokyo-night"

        # Bind the list of student numbers to the StudentNumber widget
        student_number: StudentNumber = self.query_one(StudentNumber)
        student_number.data_bind(student_numbers=self.app_state.list_student_numbers())

        # Initially disable the buildmenu until we have a commit
        self.query_one("#buildmenu").disabled = True

        # Populate the year/semester/stage dropdowns from AppState
        stage_sel: Select = self.query_one("#stage_select", Select)
        year_sel: Select = self.query_one("#year_select", Select)
        sem_sel: Select = self.query_one("#semester_select", Select)

        stage_sel.set_options([(i, i) for i in self.app_state.get_stages()])
        year_sel.set_options([(i, i) for i in self.app_state.get_years()])
        sem_sel.set_options([(i, i) for i in self.app_state.get_semesters()])

    def compose(self) -> ComposeResult:
        """Compose the primary UI layout."""
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
