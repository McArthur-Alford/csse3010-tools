import os
from serde.yaml import from_yaml
from csse3010_tools.criteria import Criteria
from csse3010_tools.gitea_api import GiteaInterface
import re

ROOT_DIR = "."
CRITERIA_PATH = os.path.join(ROOT_DIR, "criteria")

def list_files(dir: str) -> list[str]:
    file_paths: list[str] = []

    for root, _, files in os.walk(dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)

    return file_paths

def load_criteria() -> list[Criteria]:
    criterias: list[Criteria] = []
    for path in list_files(CRITERIA_PATH):
        if not path.endswith('.yaml'):
            continue

        with open(path) as file:
            data: str = file.read()
            criteria: Criteria = from_yaml(Criteria, data)
            criterias.append(criteria)

    return criterias

class AppState:
    criteria: list[Criteria]

    def reload_students(self):
        students = self.gitea.get_students()
        self.students = {student.username: student for student in students}

    def get_student_numbers(self):
        return [item for item in self.students]

    def set_active_student(self, name):
        pattern = r's\d{7}'
        if re.search(pattern, name):
            self.active_student = name
        else:
            self.active_student = None
   
    def __init__(self):
        self.criteria = load_criteria()
        self.gitea = GiteaInterface()
        self.students = {}
        self.active_student = None

        # If this becomes a big latency causer move it to somewhere asynchronous?
        self.reload_students()


if __name__ == "__main__":
    appstate: AppState = AppState()

    print(appstate.students)
