import os
import datetime
import json
from gitea import Gitea, User, Repository
from serde.json import to_json
import sys

token_path = ".access_token"
gitea_url = "https://csse3010-gitea.uqcloud.net"

design_tasks = {
    "s1": datetime.datetime(
        2025, 3, 17, 12, 00, 00, tzinfo=datetime.timezone(datetime.timedelta(hours=10))
    ),
    # Dates are not right:
    "s2": datetime.datetime(
        2025, 3, 31, 12, 00, 00, tzinfo=datetime.timezone(datetime.timedelta(hours=10))
    ),
    # "dt3": datetime.datetime(
    #     2025, 3, 17, 12, 00, 00, tzinfo=datetime.timezone(datetime.timedelta(hours=10))
    # ),
    # "dt4": datetime.datetime(
    #     2025, 3, 17, 12, 00, 00, tzinfo=datetime.timezone(datetime.timedelta(hours=10))
    # ),
}


def get_gitea_client():
    with open(token_path) as file:
        token = file.read().strip()
    return Gitea(gitea_url, token)


def is_student_user(username: str) -> bool:
    return username.startswith("s") and username[1:].isdigit()


def get_student_repos(gitea: Gitea, task_key: str):
    students = {}
    users = gitea.get_users()
    for user in users:
        if is_student_user(user.username):
            for org in user.get_orgs():
                if user.username[1:] in org.name:
                    for repo in org.get_repositories():
                        if repo.name == "repo":
                            students[user.username] = repo
                            print(f"{user.username}: {students[user.username].name}")
    return students


def load_existing_commits(filename="latest_commits.json"):
    if os.path.exists(filename):
        with open(filename, "r") as file:
            return json.load(file)
    return {}


def get_latest_commits(students, deadline, existing_commits, current_task: str):
    latest_commits = existing_commits.get(current_task, {})

    for student, repo in students.items():
        if student in latest_commits and latest_commits[student] != "No commits found":
            continue  # Skip API call if we already have a commit

        print("\n---")

        commits = repo.get_commits()
        latest_commit = None
        latest = None

        for commit in commits:
            commit_date = datetime.datetime.strptime(
                commit.created, "%Y-%m-%dT%H:%M:%S%z"
            ).astimezone(datetime.timezone(datetime.timedelta(hours=10)))
            print("Deadline:", deadline)
            print("Commit Date:", commit_date)
            if commit_date <= deadline and (latest is None or commit_date >= latest):
                latest = commit_date
                latest_commit = commit.sha
            # else:
            #     if commit_date >= deadline:
            #         print("Found a commit past the deadline, ignoring it")
            #     break
            print(latest_commit)

        latest_commits[student] = latest_commit if latest_commit else "No commits found"
        print(latest_commits[student])

    return latest_commits


def save_commits_to_json(commits, filename="latest_commits.json"):
    with open(filename, "w") as file:
        json.dump(commits, file, indent=4)
    print(f"Saved commit data to {filename}")


def main(task_name):
    if task_name not in design_tasks:
        print(f"Task {task_name} not found.")
        return

    gitea = get_gitea_client()
    deadline = design_tasks[task_name]

    print("Loading existing data")
    existing_commits = load_existing_commits()
    if task_name not in existing_commits:
        existing_commits[task_name] = {}

    print("Getting student repos")
    student_repos = get_student_repos(gitea, task_name)
    print(student_repos)
    print("Getting latest commits")
    commits = get_latest_commits(student_repos, deadline, existing_commits, task_name)
    existing_commits[task_name] = commits
    print(existing_commits)

    save_commits_to_json(existing_commits)

    for student, commit in commits.items():
        print(f"{student}: {commit}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <task_name>")
    else:
        main(sys.argv[1])
