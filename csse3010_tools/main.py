from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, HorizontalScroll, VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Select, Label, Placeholder, Button
from textual.messages import Message
from textual.suggester import SuggestFromList
from textual.reactive import reactive
from textual.widgets import Static, Rule
from textual.validation import Regex, ValidationResult
from csse3010_tools.criteria import example_criteria
from csse3010_tools.appstate import AppState

class StudentNumber(Input):
    class Updated(Message):
        def __init__(self, number) -> None:
            self.number = number
            super().__init__()
    
    student_numbers: reactive[list[str]] = reactive([])
    
    def on_mount(self):
        self.Changed.bubble = False
        self.placeholder = "sXXXXXXX"
        self.validators = [Regex("s\\d{7}")]

    def watch_student_numbers(self, old: list[str], new: list[str]):
        print(new)
        self.suggester = SuggestFromList(new,case_sensitive=False)

    @on(Input.Changed)
    def validation(self, event: Input.Changed) -> None:
        if not event.validation_result.is_valid:
            self.add_class("invalid")
        else:
            self.post_message(self.Updated(event.value))
            self.remove_class("invalid")

class StudentSelect(Horizontal):
    def compose(self):
        with Horizontal(classes="metadata_field"):
            yield Label("Student Number:")
            yield StudentNumber()

class LeftPanel(VerticalScroll):
    DEFAULT_CLASSES = "panel"

    # def state_changed(self, old_value, new_value):
    #     self.query_one("#student_number_selector", Input)
    #     print("STATE CHANGED NERD")

    # def on_mount(self):
    #     self.watch(self.app, "app_state", self.state_changed, init=False)
    
    def compose(self) -> ComposeResult:
        self.border_title = "Stage Select"
        with Horizontal(classes="metadata_field"):
            with Horizontal(classes="metadata_field"):
                yield Label("Year:")
                yield Select([("2024", 1)], allow_blank=False)
            with Horizontal(classes="metadata_field"):
                yield Label("Sem:")
                yield Select([("1", 1), ("2", 2)], allow_blank=False)
        with Horizontal(classes="metadata_field"):
            yield Label("Stage:")
            yield Input(placeholder="sX")
        yield Rule()
        yield StudentSelect()
        with Horizontal(classes="metadata_field"):
            yield Input(placeholder="Name", disabled=True)
        # yield Placeholder()

class Band(Horizontal):
    DEFAULT_CLASSES = "band"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="mark_container"):
            yield Input(classes="mark", placeholder="00")
            yield Label("/ 01")
        yield Label("Band 1")
        with Horizontal(classes="grade_grid"):
            yield Button("Exemplary", classes="grade_button")
            yield Button("Proficient", classes="grade_button")
            yield Button("Competent", classes="grade_button")
            yield Button("Insufficient", classes="grade_button")
            yield Button("Absent", classes="grade_button")

class MarkPanel(VerticalScroll):
    DEFAULT_CLASSES = "panel"

    def compose(self) -> ComposeResult:
        yield Band()
        yield Band()
        yield Band()
        yield Band()

class Body(HorizontalScroll):
    def compose(self) -> ComposeResult:
        yield LeftPanel()
        yield MarkPanel()

class Banner(Horizontal):
    version = reactive("gitea version")
    user = reactive("gitea user")

    def watch_version(self, old_version: str, new_version: str) -> None:
        self.query_one("#gitea_version", Label).update(str(new_version))

    def watch_user(self, old_user: str, new_user: str) -> None:
        self.query_one("#gitea_user", Label).update(str(new_user))
    
    def compose(self) -> ComposeResult:
        yield Label("GITEA VERSION", id="gitea_version")
        yield Label("GITEA USER", id="gitea_user")


class MarkingApp(App):
    CSS_PATH = "style.tcss"
    TITLE = "CSSE3010 Tools"
    SUB_TITLE = "Marking"
    app_state: reactive[AppState] = reactive(AppState())
    student_numbers: reactive[list[str]] = reactive([])
    active_student: reactive[str] = reactive(str)

    def watch_app_state(self) -> None:
        print("AAAAAAAAAAAAAAAAAAAAAA")

    def watch_active_student(self, old, new) -> None:
        if old == new:
            return

    def on_student_number_updated(self, message: StudentNumber.Updated) -> None:
        self.app_state.set_active_student(message.number)
        self.active_student = self.app_state.active_student
        self.mutate_reactive(MarkingApp.app_state)

    def on_mount(self) -> None:
        self.student_numbers = self.app_state.get_student_numbers()
        
        banner = self.query_one(Banner)
        banner.version = f"Gitea API {self.app_state.gitea.get_version()}"
        banner.user = self.app_state.gitea.get_user()

        student_number: StudentNumber = self.query_one(StudentNumber)
        student_number.data_bind(student_numbers=MarkingApp.student_numbers)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Vertical():
            yield Banner()
            yield Body()

# class CombiningLayoutsExample(App):
#     CSS_PATH = "combining_layouts.tcss"

#     def compose(self) -> ComposeResult:
#         yield Header()
#         with Container(id="app-grid"):
#             with VerticalScroll(id="left-pane"):
#                 for number in range(15):
#                     yield Static(f"Vertical layout, child {number}")
#             with Horizontal(id="top-right"):
#                 yield Static("Horizontally")
#                 yield Static("Positioned")
#                 yield Static("Children")
#                 yield Static("Here")
#             with Container(id="bottom-right"):
#                 yield Static("This")
#                 yield Static("panel")
#                 yield Static("is")
#                 yield Static("using")
#                 yield Static("grid layout!", id="bottom-right-final")

def main():
    app = MarkingApp()
    app.run()

if __name__ == "__main__":
    main()
