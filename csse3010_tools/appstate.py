import os
from dataclasses import dataclass
from typing import Dict, List

from serde.yaml import from_yaml

from csse3010_tools.criteria import Criteria
from csse3010_tools.gitea_api import GiteaInterface

ROOT_DIR = "."
CRITERIA_PATH = os.path.join(ROOT_DIR, "criteria")


def _list_files(directory: str) -> List[str]:
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_paths.append(os.path.join(root, file))
    return file_paths


@dataclass
class Commit:
    date: str
    hash: str
    message: str
    url: str


class AppState:
    def __init__(self):
        self._gitea = GiteaInterface()

        # Cache of {username -> StudentObject (or dict with 'username' key, etc.)}
        self._students: Dict[str, object] = {}

        # Cache of commits: {username -> list of Commit objects}
        self._commits_cache: Dict[str, List[Commit]] = {}

        # Cache of all loaded Criteria objects
        self._criteria_list: List[Criteria] = []

        # Load them all at init time
        self.reload_students()
        self._load_criteria()

    def reload_students(self):
        """Fetches all students from Gitea and caches them in a dict by username."""
        students = self._gitea.get_students()
        self._students = {student.username: student for student in students}

    def _load_criteria(self):
        """Loads all .yaml criteria files into memory for quick searching."""
        all_paths = _list_files(CRITERIA_PATH)
        self._criteria_list = []
        for path in all_paths:
            if not path.endswith(".yaml"):
                continue
            with open(path, "r") as file:
                data = file.read()
                crit = from_yaml(Criteria, data)
                self._criteria_list.append(crit)

    def _get_commits_for_student(self, student_number: str) -> List[Commit]:
        """
        Fetches commits from Gitea (if not cached), then returns them from cache.
        """
        if student_number not in self._commits_cache:
            raw_commits = self._gitea.get_commits(student_number)
            commits = [
                Commit(
                    date=c["date"],
                    hash=c["hash"],
                    message=c["message"],
                    url=c["url"]
                )
                for c in raw_commits
            ]
            self._commits_cache[student_number] = commits
        return self._commits_cache[student_number]

    @property
    def user(self) -> str:
        return self._gitea.get_user()
    
    @property
    def student_numbers(self) -> List[str]:
        return list(self._students.keys())

    def commits(self, student_number: str) -> List[Commit]:
        return self._get_commits_for_student(student_number)

    def criteria(self, year: str, semester: str, task: str) -> Criteria:
        for crit in self._criteria_list:
            # Ensure the Criteria object exposes these attributes (crit.year, crit.semester, crit.stage)
            if (crit.year == year) and (crit.semester == semester) and (crit.stage == task):
                return crit
        raise FileNotFoundError(f"No matching criteria found for {year=}, {semester=}, {task=}")

    def clone_repo(self, student_number: str, commit_hash: str) -> None:
        local_dir = "temporary/repo"
        self._gitea.clone_repo(student_number, commit_hash, local_dir)

    def clone_marks(self) -> None:
        local_dir = "temporary/marks"
        self._gitea.clone_marks(local_dir)

    def write_marks(self, criteria: Criteria, student_number: str, marks) -> None:
        local_dir = "temporary/marks"

        self._gitea.pull_marks(local_dir)

        # Write the marks to the correct location inside the local_dir
        # Requires converting them to .md tables and some other shenanigans
        # TODO

        self._gitea.push_marks(local_dir)
