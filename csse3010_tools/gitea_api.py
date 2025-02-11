import os
from gitea import Gitea, User, Organization, Repository, Commit
import requests
import re
from git import Repo

# GITEA API Stuff
TOKEN_PATH = ".access_token"
URL = "https://csse3010-gitea.uqcloud.net"


def gitea_clone_repo(repo, commit_hash: str, directory: str) -> None:
    url = ""
    if isinstance(repo, Repository):
        url = repo.ssh_url
    else:
        url = repo
    try:
        repo = Repo(directory)
    except:
        if os.path.exists(directory):
            os.removedirs(directory)
        try:
            repo = Repo.clone_from(url, directory)
        except:
            print("Marks repo doesnt exist!")

    if commit_hash is not None:
        repo.git.checkout(commit_hash)


class GiteaInterface:
    key: str

    def __init__(self):
        with open(TOKEN_PATH) as file:
            self.key = file.read().rstrip()
            self.gitea = Gitea(URL, self.key)

    def get_version(self) -> str:
        return self.gitea.get_version()

    def get_user(self) -> str:
        return self.gitea.get_user().username

    def get_users(self) -> list[User]:
        users = self.gitea.get_users()
        return users

    def is_student(self, student: User) -> bool:
        pattern = r"s\d{7}"
        if re.search(pattern, student.username):
            return True
        else:
            return False

    def get_students(self) -> list[User]:
        users = self.get_users()
        return [user for user in users if self.is_student(user)]

    def get_orgs(self, student: User) -> list[Organization]:
        orgs = student.get_orgs()
        return orgs

    def get_repo(self, student: User) -> Repository:
        username = student.username
        if not self.is_student(student):
            return None

        # Can this cause a lot of api calls? Probs no more than 3 or 4, but if there are issues with overuse this is a place to look
        orgs = self.get_orgs(student)
        for org in orgs:
            if username[1:] not in org.name:
                continue

            repos = org.get_repositories()
            for repo in repos:
                if repo.name == "repo":
                    return repo

    # def get_mark_repo(self) -> Repository:
    #     self.gitea.

    # commits = self.get_repo(student).get_commits()
    # from pprint import pprint
    # urls = [commit.html_url for commit in commits if commit.sha == commit_hash]
    # if len(urls) != 1:
    #     print("too many or no urls matching that hash")
    #     return

    # url = urls[0]
    # Repo.clone_from(url, directory)


if __name__ == "__main__":
    instance = GiteaInterface()
    students = instance.get_students()
    from pprint import pprint

    instance.get_repo(students[0])
    instance.get_repo(students[5])
    # orgs = instance.get_orgs(students[5])
    # pprint(orgs)

    # for org in orgs:
    #     pprint(org.name)
