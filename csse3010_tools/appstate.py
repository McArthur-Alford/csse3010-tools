import shutil
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from git import Repo
from gitea import Gitea, User, Organization, Repository, Commit
from serde.yaml import from_yaml

from csse3010_tools.rubric import Rubric

TOKEN_PATH = ".access_token"
GITEA_URL = "https://csse3010-gitea.uqcloud.net"


def _list_files(directory: str) -> List[str]:
    """
    Recursively list all files in the given directory.
    """
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_paths.append(os.path.join(root, file))
    return file_paths


@dataclass
class CommitInfo:
    date: str
    hash: str
    message: str
    url: str


class AppState:
    def __init__(self):
        # Internal "state" fields
        self._year: Optional[str] = None
        self._semester: Optional[str] = None
        self._stage: Optional[str] = None
        self._student_number: Optional[str] = None
        self._commit_hash: Optional[str] = None
        self._rubric: Optional[Rubric] = None

        # Gitea client
        self._gitea = self._init_gitea()

        # In-memory caches
        self._students: Dict[str, User] = {}
        self._criteria_list: List[Rubric] = []
        self._commits_cache: Dict[str, List[CommitInfo]] = {}

        # Initial loading
        self._load_students()
        self._load_criteria()

    @property
    def year(self) -> Optional[str]:
        return self._year

    @year.setter
    def year(self, value: str):
        if value != self._year:
            self._year = value
            self._clone_marks_repo_if_ready()
            self._reload_rubric()

    @property
    def semester(self) -> Optional[str]:
        return self._semester

    @semester.setter
    def semester(self, value: str):
        if value != self._semester:
            self._semester = value
            self._clone_marks_repo_if_ready()
            self._reload_rubric()

    @property
    def stage(self) -> Optional[str]:
        return self._stage

    @stage.setter
    def stage(self, value: str):
        self._stage = value
        self._reload_rubric()

    @property
    def student_number(self) -> Optional[str]:
        return self._student_number

    @student_number.setter
    def student_number(self, value: str):
        if value != self._student_number:
            self._student_number = value
            self._commit_hash = None  # Clear the commit hash to avoid confusion
            self._clone_student_repo()
            self._reload_rubric()

    @property
    def commit_hash(self) -> Optional[str]:
        return self._commit_hash

    @commit_hash.setter
    def commit_hash(self, value: str):
        if value != self._commit_hash:
            self._commit_hash = value
            self._clone_student_repo()

    @property
    def rubric(self) -> Optional[Rubric]:
        """Returns the currently loaded rubric, if any"""
        return self._rubric

    @rubric.setter
    def rubric(self, value: Rubric):
        self._rubric = value
        self._rubric.on_change(self._write_marks)
        self._write_marks()

    def get_semesters(self) -> List[str]:
        """
        Returns the distinct semesters across all loaded criteria.
        """
        return sorted(list({crit.sem for crit in self._criteria_list}))

    def get_years(self) -> List[str]:
        """
        Returns the distinct years across all loaded criteria.
        """
        return sorted(list({crit.year for crit in self._criteria_list}))

    def get_stages(self) -> List[str]:
        """
        Returns the distinct stage names (like S1, PF, etc.) across all loaded criteria.
        """
        return sorted(list({crit.name for crit in self._criteria_list}))

    def list_student_numbers(self) -> List[str]:
        """
        Returns all known student usernames/numbers (e.g., s1234567).
        """
        return list(self._students.keys())

    def get_student_name(self, student_number: str) -> Optional[str]:
        """
        Returns the full name for the given student number, if known.
        """
        user = self._students.get(student_number)
        return user.full_name if user else None

    def get_criteria(self, year: str, semester: str, task: str) -> Rubric:
        """
        Searches loaded rubrics for one matching the given year, semester, and task (stage).
        Raises FileNotFoundError if no matching rubric is found.
        """
        for crit in self._criteria_list:
            if crit.year == year and crit.sem == semester and crit.name == task:
                return crit
        raise FileNotFoundError(
            f"No matching criteria found for {year=}, {semester=}, {task=}"
        )

    def list_commits(self, student_number: str) -> List[CommitInfo]:
        """
        Returns a list of the commits from the student's 'repo' repository,
        caching results to avoid repeated API calls.
        """
        if student_number not in self._commits_cache:
            student = self._students.get(student_number)
            if not student:
                return []

            repo = self._get_student_repo(student)
            if not repo:
                return []

            commits = []
            for c in repo.get_commits():
                commits.append(
                    CommitInfo(
                        date=c.created,
                        hash=c.sha,
                        message=c._commit["message"],
                        url=c._html_url,
                    )
                )
            self._commits_cache[student_number] = commits

        return self._commits_cache[student_number]

    def _read_marks(self) -> str:
        """
        Reads the marks for the given student_number and stage from the
        local cloned marks repository, returning the raw markdown string.
        """
        if not self._student_number or not self._stage:
            return

        marks_dir = self._marks_directory
        stage_dir = self._normalize_stage_dir(self._stage)
        student_id = self._student_number[1:]  # e.g. strip 's' from 's1234567'

        for i in range(10):
            path = os.path.join(marks_dir, f"{student_id}{i}", stage_dir, "marks.md")
            if os.path.exists(path):
                with open(path, "r") as f:
                    return f.read()
        return ""

    def _write_marks(self) -> None:
        """
        Writes the given Rubric object as markdown to the marks.md file
        for the specified student_number and stage.
        """
        if not self._stage or not self._student_number or not self._rubric:
            return

        marks_dir = self._marks_directory
        stage_dir = self._normalize_stage_dir(self._stage)
        md_content = Rubric.into_md(self._rubric)
        student_id = self._student_number[1:]  # e.g. strip 's' from 's1234567'

        for i in range(10):
            path = os.path.join(marks_dir, f"{student_id}{i}", stage_dir)
            if os.path.exists(path):
                path = os.path.join(path, "marks.md")
                with open(path, "w") as f:
                    f.write(md_content)
                    print(f"Wrote marks to {path}")
                return  # Once we find and write, we're done.

        print(f"Failed to write marks for {self._student_number}")

    def _init_gitea(self) -> Gitea:
        """
        Initializes the Gitea client using the token in TOKEN_PATH.
        """
        with open(TOKEN_PATH) as file:
            token = file.read().strip()
        return Gitea(GITEA_URL, token)

    def _load_students(self):
        """
        Load all students (sXXXXXXX accounts) and cache them.
        """
        users = self._gitea.get_users()
        for user in users:
            if self._is_student_user(user):
                self._students[user.username] = user

    def _load_criteria(self):
        """
        Loads all .yaml criteria files into memory for quick searching.
        """
        criteria_root = os.path.join(".", "criteria")
        all_paths = _list_files(criteria_root)

        self._criteria_list.clear()
        for path in all_paths:
            if path.endswith(".yaml"):
                with open(path, "r") as file:
                    data = file.read()
                    crit = Rubric.from_yaml(data)
                    self._criteria_list.append(crit)

    def _is_student_user(self, user: User) -> bool:
        pattern = r"s\d{7}"
        return bool(re.search(pattern, user.username))

    def _clone_marks_repo_if_ready(self):
        if self._year and self._semester:
            self._clone_marks_repo()

    def _reload_rubric(self) -> None:
        """
        Try to load the rubric for the current year/semester/stage from .yaml.
        If found, store it in self._rubric. If not found, set self._rubric = None.
        If we have a student set, also read the student's existing marks from .md
        into the rubric, then write it back to ensure everything stays synced.
        """
        if not all([self._year, self._semester, self._stage]):
            self._rubric = None
            return

        # Attempt to load from YAML
        try:
            loaded = self.get_criteria(self._year, self._semester, self._stage)
        except FileNotFoundError:
            print(f"No matching rubric for {self._year}/{self._semester}/{self._stage}")
            self._rubric = None
            return

        loaded.clear_marks()

        # If we have a student selected, try to read that student's .md
        if self._student_number:
            existing_md = self._read_marks()
            if existing_md:
                loaded.load_md(existing_md)

        self.rubric = loaded

    def _clone_student_repo(self) -> None:
        """
        Clones the current student's repository into temporary/repo/<student_number>.
        If sefl._commit_hash is not None, checks out that commit.
        If the directory already exists, tries to open it as a git repo and optionally
        checkout the commit. If that fails, removes the directory and starts fresh.
        """
        if not self._student_number:
            return

        student = self._students.get(self._student_number)
        if not student:
            print(f"No student found for {self._student_number}")
            return

        repo = self._get_student_repo(student)
        if not repo:
            print(f"No repository found for student {self._student_number}")
            return

        local_dir = os.path.join("temporary", "repo", self._student_number)

        if not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
            try:
                print(f"Cloning {self._student_number}'s repo into: {local_dir}")
                cloned_repo = Repo.clone_from(repo.ssh_url, local_dir)
                if self._commit_hash:
                    cloned_repo.git.checkout(self._commit_hash)
            except Exception as e:
                print(f"Could not clone {self._student_number}'s repo:\n{e}")
        else:
            # Directory exists: check if it's a valid repo
            try:
                existing_repo = Repo(local_dir)
                if self._commit_hash:
                    existing_repo.git.checkout(self._commit_hash)
                print(
                    f"Repo for {self._student_number} already exists; used existing clone."
                )
            except Exception as e:
                print(
                    f"Existing directory is invalid or corrupted ({e}). Removing and re-cloning."
                )
                shutil.rmtree(local_dir)
                os.makedirs(local_dir, exist_ok=True)
                try:
                    cloned_repo = Repo.clone_from(repo.ssh_url, local_dir)
                    if self._commit_hash:
                        cloned_repo.git.checkout(self._commit_hash)
                except Exception as e2:
                    print(f"Failed to re-clone {self._student_number}'s repo:\n{e2}")

    def _clone_marks_repo(self):
        """
        Clones the marks repo for the currently selected semester/year,
        if not already cloned. It does NOT pull or overwrite any changes
        to avoid accidental data loss.
        """
        url = f"git@csse3010-gitea.zones.eait.uq.edu.au:uqmdsouz/marking_sem{self._semester}_{self._year}.git"
        repo_dir = self._marks_directory

        if not os.path.exists(repo_dir):
            os.makedirs(repo_dir, exist_ok=True)
            try:
                print(f"Cloning marks repo into: {repo_dir}")
                Repo.clone_from(url, repo_dir)
            except Exception as e:
                print(f"Could not clone marks repo:\n{e}")

    @property
    def _marks_directory(self) -> str:
        """
        Returns the local directory path where the marks repo is stored.
        e.g. ./temporary/marks_sem2_2025 for sem=2, year=2025.
        """
        if not self._semester or not self._year:
            raise RuntimeError("must have a proper marks directory")
        return f"./temporary/marks_sem{self._semester}_{self._year}"

    def _normalize_stage_dir(self, stage: str) -> str:
        """
        For a given stage string (e.g. 'pf', '1', 'S2'), returns
        the directory name as 'pf' or 's1', 's2' etc.
        """
        stage = stage.lower()
        if stage != "pf" and not stage.startswith("s"):
            stage = f"s{stage}"
        return stage

    def _get_student_repo(self, student: User) -> Optional[Repository]:
        """
        Given a student user, find their 'repo' repository inside an org
        that corresponds to their student number.
        """
        if not self._is_student_user(student):
            return None
        username = student.username
        # We try to find an org that "contains" the last digits of the username
        for org in student.get_orgs():
            if username[1:] in org.name:
                for r in org.get_repositories():
                    if r.name == "repo":
                        return r
        return None


# Example usage:
if __name__ == "__main__":
    app_state = AppState()
    print("Current Gitea user:", app_state._gitea.get_user().username)

    # Setting year/semester triggers marks repo cloning automatically
    app_state.year = "2024"
    app_state.semester = "2"
    app_state.stage = "pf"

    print("Available years:", app_state.get_years())
    print("Available semesters:", app_state.get_semesters())
    print("Available stages:", app_state.get_stages())
    print(f"Loaded rubric:\n{app_state.rubric.into_md()}")
