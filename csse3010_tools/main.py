from typing import Optional

from textual import on
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

    app_state: AppState = AppState()
    active_student: reactive[str] = reactive("")
    active_commit: reactive[Optional[str]] = reactive(None)
    current_criteria: reactive[Rubric | None] = reactive(None)
    marks_changed: reactive[bool] = reactive(False)
    active_stage: reactive[str] = reactive("")

    def write_marks(self) -> None:
        if self.current_criteria is None or self.active_student == "":
            print("Unable to write file")
            return
        self.app_state.write_marks(
            self.current_criteria, self.active_student, self.active_stage
        )

    def load_marks(self) -> None:
        # Load the marks from the students file into the md
        # If there is an error with the file, override the label so the user knows
        # But otherwise let them modify/save their own 0ed out version to fix it
        if self.current_criteria is None or self.active_student == "":
            print("Unable to load file")
            return
        md = self.app_state.read_marks(self.active_student, self.active_stage)
        self.current_criteria.load_md(md)
        self.build_criteria_panel()

    def watch_marks_changed(self) -> None:
        label = self.query_one("#save_label", Label)
        # if self.marks_changed:
        #     label.update("Out of date with .md file")
        # else:
        #     label.update("Up to date with .md file")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_button":
            print("Saving")
            self.write_marks()
        if event.button.id == "load_button":
            print("Loading")
            self.load_marks()

    @on(CommentInput.CommentChanged)
    def on_comment_changed(self, _message: CommentInput.CommentChanged) -> None:
        if self.current_criteria is None:
            return

        markpanel = self.query_one(MarkPanelRaw)
        markpanel.text = self.current_criteria.into_md()
        self.write_marks()

    @on(MarkSelected)
    def on_mark_selected(self, _message: MarkSelected) -> None:
        if self.current_criteria is None or _message is None:
            return

        # Write the marks to the log
        markpanel = self.query_one(MarkPanelRaw)
        markpanel.text = self.current_criteria.into_md()
        print(_message)
        self.write_marks()

    def watch_app_state(self) -> None:
        """Called whenever app_state is mutated (if we call self.mutate_reactive)."""
        print("App State changed")

    def watch_active_student(self, old: str, new: str) -> None:
        """When the user picks a new student, we can refresh the commit hash dropdown's choices."""
        if old == new or new == "":
            return
        print(f"Active student changed from {old} to {new}")
        commit_hash_dropdown = self.query_one("#commit-hash-dropdown", Select)
        commits = self.app_state.commits(self.active_student)
        commit_hash_dropdown.set_options(
            [(f"{commit.hash[:16]}\n{commit.date}", commit.hash) for commit in commits]
        )
        commit_hash_dropdown.clear()

    @on(StudentNumber.Updated)
    def on_student_number_updated(self, message: StudentNumber.Updated) -> None:
        """User selected a student number."""

        if message.valid:
            self.active_commit = None
            self.active_student = message.number

            student_name = self.query_one("#StudentName", Input)
            student = self.app_state.student_name(message.number)
            student_name.value = student

            self.query_one(TabbedContent).disabled = False

            self.app_state.clone_repo(message.number)

            self.load_marks()

            self.query_one("#save_label", Label).update(f"Marking {message.number}")
        else:
            self.active_student = ""
            self.active_commit = None

            self.query_one(TabbedContent).disabled = True

            self.query_one("#save_label", Label).update("No Student Selected")

    @on(CommitHashSelect.Updated)
    def on_commit_hash_updated(self, message: CommitHashSelect.Updated) -> None:
        """User selected a commit hash from the dropdown."""
        self.active_commit = message.commit_hash
        if self.active_student == "":
            return

        self.query_one("#buildmenu").disabled = False
        if message.commit_hash == "":
            self.query_one("#buildmenu").disabled = True
            return

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
        self.app_state.reload_marks(year, sem)

        self.active_stage = stage

        try:
            self.current_criteria = self.app_state.criteria(year, sem, stage)
        except FileNotFoundError:
            print(f"No criteria file found for {year}/{sem}/{stage}")
            self.current_criteria = None

        self.build_criteria_panel()
        self.load_marks()

    def build_criteria_panel(self) -> None:
        """
        Clears the MarkPanel and populates it based on the current_criteria.
        """
        mark_panels = self.query("#mark_panel")
        for mark_panel in mark_panels:
            mark_panel.remove_children()

            if self.current_criteria:
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

        # Initially disable the buildmenu until a hash is gotten
        self.query_one("#buildmenu").disabled = True

        # Slot all the possible year/sem/stage names into the git select
        stage_sel: Select = self.query_one("#stage_select", Select)
        year_sel: Select = self.query_one("#year_select", Select)
        sem_sel: Select = self.query_one("#semester_select", Select)
        stage_sel.set_options([(i, i) for i in self.app_state.get_stages()])
        year_sel.set_options([(i, i) for i in self.app_state.get_years()])
        sem_sel.set_options([(i, i) for i in self.app_state.get_semesters()])

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
