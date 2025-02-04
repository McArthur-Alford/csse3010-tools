import os
from gitea import Gitea, User, Organization, Repository
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from serde.yaml import from_yaml

from csse3010_tools.criteria import Rubric, load_rubric_from_yaml, rubric_to_markdown_table
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
        self._gitea.clone_repo(url, None, "./temporary/marks")

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
                crit = load_rubric_from_yaml(data)
                self._criteria_list.append(crit)

    def read_marks(self, student: str, stage: str) -> str:
        """
           reads the marks for the student, of the specific stage, as a md table 
           student: student number minus the s
           stage: stage number with the s
        """
        out = ""
        s = f"s{stage}" if stage != "pf" else "pf"
        for i in range(10):
            # i is the final digit, one of these has to match, it should be unique?
            path = f"./temporary/marks/{student[1:]}{i}/{s}/marks.md";
            if os.path.exists(path):
                with open(path, "r") as f:
                    out = f.read()

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
                Commit(
                   item.created,
                   item.sha,
                   item._commit["message"],
                   item._html_url
               ) for item in repo.get_commits()
            ]
            self._commits_cache[student_number] = commits
        return self._commits_cache[student_number]
            

    def criteria(self, year: str, semester: str, task: str) -> Rubric:
        for crit in self._criteria_list:
            if (crit.year == year) and (crit.semester == semester) and (crit.stage == task):
                return crit
        print(self._criteria_list)
        raise FileNotFoundError(f"No matching criteria found for {year=}, {semester=}, {task=}")

    def clone_repo(self, student_number: str, commit_hash: Optional[str] = None) -> None:
        directory = f"./temporary/repo/{student_number}"
        if not os.path.exists(directory):
            os.makedirs(directory)
        repo = self._gitea.get_repo(self._students[student_number])
        self._gitea.clone_repo(repo, commit_hash, directory)

    def clone_marks(self) -> None:
        local_dir = "temporary/marks"
        self._gitea.clone_marks(local_dir)

    def write_marks(self, criteria: Rubric, student_number: str, stage: str) -> None:
        local_dir = "temporary/marks"

        # self._gitea.pull_marks(local_dir)

        out = ""
        s = f"s{stage}" if stage != "pf" else "pf"
        for i in range(10):
            # i is the final digit, one of these has to match, it should be unique?
            path = f"./temporary/marks/{student_number[1:]}{i}/{s}/marks.md";
            if os.path.exists(path):
                with open(path) as f:
                    f.write(rubric_to_markdown_table(criteria))
                    

        # self._gitea.push_marks(local_dir)
