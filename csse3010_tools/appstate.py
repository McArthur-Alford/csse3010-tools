# What does the app need to do?
# Helpers:
# - Student number conversion (+/- s, match with wildcard last digit)
# Actual stuff:
# - Clone the marks repo if it isnt already there. DO NOT overwrite/pull in case of changes
# - Get a mapping of student numbers to commits (hash + date + message)
# - Clone a students repo with a student number and hash
# - Load md string from marks
# - Save md string to marks
# - Build, Run, Flash & Clean using matts existing scripts for simplicity

import os
from gitea import Gitea, User, Organization, Repository
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from serde.yaml import from_yaml

from csse3010_tools.rubric import Rubric
from csse3010_tools.gitea_api import GiteaInterface, gitea_clone_repo

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
        self._students: Dict[str, User] = {}

        # Cache of commits: {username -> list of Commit objects}
        self._commits_cache: Dict[str, List[Commit]] = {}

        # Cache of all loaded Criteria objects
        self._criteria_list: List[Rubric] = []

        # Load them all at init time
        self.reload_students()
        self._load_criteria()

    def reload_marks(self, year, sem):
        url = f"git@csse3010-gitea.zones.eait.uq.edu.au:uqmdsouz/marking_sem{sem}_{year}.git"
        # url =  f"https://csse3010-gitea.uqcloud.net/uqmdsouz/marking_sem{sem}_{year}.git"
        gitea_clone_repo(url, None, f"./temporary/marks")

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
                crit = Rubric.from_yaml(data)
                self._criteria_list.append(crit)

    def get_semesters(self):
        out = []
        for crit in self._criteria_list:
            out.append(crit.sem)
        return out

    def get_stages(self):
        out = []
        for crit in self._criteria_list:
            out.append(crit.name)
        return out

    def get_years(self):
        out = []
        for crit in self._criteria_list:
            out.append(crit.year)
        return out

    @property
    def user(self) -> str:
        return self._gitea.get_user()

    @property
    def student_numbers(self) -> List[str]:
        return list(self._students.keys())

    def student_name(self, student_number: str) -> str:
        return self._students[student_number].full_name

    def commits(self, student_number: str) -> List[Commit]:
        if student_number not in self._commits_cache:
            student = self._students[student_number]
            repo = self._gitea.get_repo(student)
            commits: List[Commit] = [
                Commit(item.created, item.sha, item._commit["message"], item._html_url)
                for item in repo.get_commits()
            ]
            self._commits_cache[student_number] = commits
        return self._commits_cache[student_number]

    def criteria(self, year: str, semester: str, task: str) -> Rubric:
        for crit in self._criteria_list:
            if (crit.year == year) and (crit.sem == semester) and (crit.name == task):
                return crit
        print(self._criteria_list)
        raise FileNotFoundError(
            f"No matching criteria found for {year=}, {semester=}, {task=}"
        )

    def clone_marks(self) -> None:
        local_dir = "temporary/marks"
        self._gitea.clone_marks(local_dir)

    def write_marks(self, criteria: Rubric, student_number: str, stage: str) -> None:
        s = stage.lower()
        if stage != "pf" and s[0] != "s":
            s = f"s{stage}"

        for i in range(10):
            # i is the final digit, one of these has to match, it should be unique?
            path = f"./temporary/marks/{student_number[1:]}{i}/{s}/marks.md"
            if os.path.exists(path):
                with open(path, "w") as f:
                    f.write(Rubric.into_md(criteria))

    def read_marks(self, student: str, stage: str) -> str:
        """
        reads the marks for the student, of the specific stage, as a md table
        student: student number minus the s
        stage: stage number with the s
        """
        out = ""

        s = stage.lower()
        if stage != "pf" and s[0] != "s":
            s = f"s{stage}"

        for i in range(10):
            # i is the final digit, one of these has to match, it should be unique?
            path = f"./temporary/marks/{student[1:]}{i}/{s}/marks.md"
            if os.path.exists(path):
                with open(path, "r") as f:
                    out = f.read()

        print("Out was:")
        print("Out was:")
        print("Out was:")
        print(out)

        return out
