import os
from typing import Optional
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Vertical, Container
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
from subprocess import PIPE, Popen, STDOUT

from csse3010_tools.appstate import AppState
from csse3010_tools.ui.banner import Banner
from csse3010_tools.ui.build_menu import BuildMenu, BuildCommand
from csse3010_tools.ui.commit_hash_select import CommitHashSelect
from csse3010_tools.ui.criteria_select import CriteriaSelect
from csse3010_tools.ui.git_select import GitSelect
from csse3010_tools.ui.mark_panel import MarkPanel, MarkSelected, CommentInput
from csse3010_tools.ui.student_select import StudentNumber
from csse3010_tools.ui.mark_panel_raw import MarkPanelRaw


class Body(Container):
    """Primary container for the main UI content."""

    def compose(self) -> ComposeResult:
        yield GitSelect()
        yield CriteriaSelect()
        # TabbedContent disabled by default until a student is set
        with TabbedContent(initial="marking", disabled=True):
            with TabPane("Marking", id="marking"):
                with Vertical(id="mark_panel"):
                    yield Label("No rubric loaded yet...")
            with TabPane("Marking Output Preview", id="markingraw"):
                yield MarkPanelRaw()
            with TabPane("Build/Run", id="buildmenu"):
                yield BuildMenu()
            with TabPane("Code Viewer", id="viewer"):
                yield Log()


class MarkingApp(App):
    """Textual application for CSSE3010 marking and repo management."""

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

    app_state: AppState

    active_commit: reactive[Optional[str]] = reactive(None)

    def __init__(self):
        super().__init__()
        self.app_state = AppState(self)

    def on_mount(self) -> None:
        """Initialize the UI after the app mounts."""
        # self.theme = "tokyo-night"

        # Populate the student selector with known student numbers
        student_number_widget: StudentNumber = self.query_one(StudentNumber)
        student_number_widget.data_bind(
            student_numbers=self.app_state.list_student_numbers()
        )

        # Build/Run menu initially disabled until a commit hash is chosen
        self.query_one("#buildmenu").disabled = True

        # Populate the year/semester/stage dropdowns from AppState
        self.query_one("#stage_select", Select).set_options(
            [(stage, stage) for stage in self.app_state.get_stages()]
        )
        self.query_one("#year_select", Select).set_options(
            [(year, year) for year in self.app_state.get_years()]
        )
        self.query_one("#semester_select", Select).set_options(
            [(sem, sem) for sem in self.app_state.get_semesters()]
        )

    def compose(self) -> ComposeResult:
        """Compose the primary layout."""
        yield Header()
        yield Footer()
        with Vertical():
            yield Banner()
            yield Body()

    @on(StudentNumber.Updated)
    async def on_student_number_updated(self, event: StudentNumber.Updated) -> None:
        """Event: User selected (or cleared) a student number."""
        if event.valid:
            self.app_state.student_number = event.number
            self._build_criteria_panel()

            # Show the student's full name (if known)
            student_name_input = self.query_one("#StudentName", Input)
            student_full_name = self.app_state.get_student_name(event.number)
            student_name_input.value = student_full_name or "Unknown Name"

            self.app_state.refresh_current_hash()

            commit_hash_dropdown = self.query_one("#commit-hash-dropdown", Select)
            commits = self.app_state.list_commits(self.app_state.student_number)
            commit_hash_dropdown.set_options(
                [
                    (f"{commit.hash[:16]}\n{commit.date}", commit.hash)
                    for commit in commits
                ]
            )
            commit_hash_dropdown.clear()

            self._update_commit_dropdown()

            # Enable the TabbedContent (Marking, etc.)
            self.query_one(TabbedContent).disabled = False
            # self.query_one("#save_label", Label).update(f"Marking {event.number}")
        else:
            # Invalid or cleared student means we disable Marking
            self.app_state.student_number = None
            self.query_one(TabbedContent).disabled = True
            # self.query_one("#save_label", Label).update("No Student Selected")

    @on(CommitHashSelect.Updated)
    async def on_commit_hash_updated(self, event: CommitHashSelect.Updated) -> None:
        """Event: User selected (or cleared) a commit hash."""
        self.active_commit = event.commit_hash or None
        self.app_state.commit_hash = self.active_commit

        # Enable/disable the buildmenu accordingly
        build_menu = self.query_one("#buildmenu")
        build_menu.disabled = self.active_commit is None

        # Update tooltip for the commit dropdown with commit message
        commit_dropdown = self.query_one("#commit-hash-dropdown", Select)
        commits = self.app_state.list_commits(self.app_state.student_number or "")
        matching = [c for c in commits if c.hash == (self.active_commit or "")]
        if matching:
            commit_dropdown.tooltip = matching[0].message
        else:
            commit_dropdown.tooltip = ""

    def _update_commit_dropdown(self) -> None:
        """Updates the commit hash dropdown with the latest commits."""
        commit_hash_dropdown = self.query_one("#commit-hash-dropdown", Select)

        # commits = self.app_state.list_commits(self.app_state.student_number or "")

        if self.app_state.commit_hash:
            commit_hash_dropdown.value = self.app_state.commit_hash

    @on(CriteriaSelect.Picked)
    def on_criteria_picked(self, event: CriteriaSelect.Picked) -> None:
        """Event: User changed year/semester/stage in the criteria picker."""
        self.app_state.year = event.year
        self.app_state.semester = event.semester
        self.app_state.stage = event.stage

        # Now rebuild the MarkPanel with the new rubric (if any)
        self.app_state.refresh_current_hash()
        self._build_criteria_panel()

        self._update_commit_dropdown()


    @on(MarkSelected)
    def on_mark_selected(self, _event: MarkSelected) -> None:
        """
        When a user picks or changes a mark in the rubric, we update the
        MarkPanelRaw text to show the new MD from AppState's rubric.
        """
        if self.app_state.rubric:
            raw_panel = self.query_one(MarkPanelRaw)
            raw_panel.text = self.app_state.rubric.into_md()

    @on(CommentInput.CommentChanged)
    def on_comment_changed(self, _event: CommentInput.CommentChanged) -> None:
        """
        When a comment changes in the rubric, we similarly refresh
        the MarkPanelRaw display text from AppState's rubric.
        """
        if self.app_state.rubric:
            raw_panel = self.query_one(MarkPanelRaw)
            raw_panel.text = self.app_state.rubric.into_md()

    @on(BuildCommand)
    @work(exclusive=True, thread=True)
    def on_buildcommand(self, message: BuildCommand) -> None:
        if self.app_state.stage is None:
            self.notify(message="No stage selected.", severity="warning")
            return
        if "SOURCELIB_ROOT" not in os.environ:
            self.notify(message="SOURCELIB_ROOT is not set.", severity="error")
            return
        stage = self.app_state._normalize_stage_dir(self.app_state.stage)
        command = f"cd $SOURCELIB_ROOT/../repo/{stage}"
        if message.type == "build":
            command += " && make"
        if message.type == "flash":
            command += " && make && make flash"
        if message.type == "clean":
            command += " && make clean"
        log = self.query_one("#buildlog", Log)
        with Popen(command, shell=True, stdout=PIPE, stderr=STDOUT) as p:
            for line in p.stdout:
                log.write_line(line.decode('utf8'))


    def _build_criteria_panel(self) -> None:
        """Clears and re-populates the MarkPanel area with the current rubric."""
        mark_panels = self.query("#mark_panel")
        for panel in mark_panels:
            panel.remove_children()
            if self.app_state.rubric:
                panel.mount(MarkPanel(self.app_state.rubric))
            else:
                panel.mount(Label("No rubric loaded for this selection."))


def main():
    MarkingApp().run()


if __name__ == "__main__":
    main()
