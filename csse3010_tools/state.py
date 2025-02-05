class State:
    # The state is a semi state machine representing the state of the app
    # States:
    # - Basic
    #   - Ensures repos are pulled, up to date
    #   - Loads the lists of students, criterias
    # - Student
    #   - A student is selected.
    # - Repo
    #   - A repo is selected
    # - Criteria

    # The marks repo url, necessary to pull down marks
    # git@csse3010-gitea.zones.eait.uq.edu.au:uqmdsouz/marking_sem{sem}_{year}.git
    marks_repo: str

    # Lets us load their hashes when set:
    student: str

    # Lets us load the markpanel (also needs student picked):
    year: str
    sem: str
    stage: str
