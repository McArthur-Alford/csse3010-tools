from serde import serde
from enum import Enum
from typing import List, Union
from dataclasses import dataclass, field

# Things to track:
# Loaded Criteria/Stage
# Student/Repo Selection
# Marks

@serde
@dataclass
class Defered:
    direction: str = ""
    def __init__(self, dir: str):
        if dir.lower() not in ["up", "down"]:
            raise Exception(f"Defer direction should be up or down, was {dir}")
        self.direction = dir.lower()

@serde
@dataclass
class Direct:
    text: str = ""
    def __init__(self, text: str):
        self.text = text

@serde
@dataclass
class Empty:
    def __init__(self):
        pass

# A criterion can either be direct, defered, or empty
Criterion = Union[Direct, Defered, Empty]

@serde
@dataclass
class Band:
    band_name: str
    criteria: List[Criterion]

@serde
@dataclass
class Category:
    category_id: str
    bands: List[Band]

@serde
@dataclass
class Task:
    task_name: str
    description: str
    categories: List[Category]

@serde
@dataclass
class Criteria():
    year: str
    semester: str
    stage: str
    tasks: List[Task]

# Example criteria from project
example_criteria = Criteria(
    year="2024", 
    semester="1", 
    stage="0", 
    tasks=[
    Task(
        task_name="RCM System",
        categories=[
            Category(
                category_id="1.a/b",
                bands=[
                    Band(
                        band_name="a",
                        criteria=[
                            Direct("All movement functions fully work without errors."),
                            Defered("Up"),
                            Direct("All movement functions are implemented but errors occur."),
                            Direct("More than half the movement functions are implemented and work with no errors."),
                            Direct("Less than half the movement functions are implemented and at least partially work."),
                            Direct("None of the movement functions work")
                        ]
                    ),
                    Band(
                        band_name="b",
                        criteria=[
                            Direct("Status LEDs and LTA1000G work correctly."),
                            Defered("Down"),
                            Defered("Down"),
                            Direct("Status LEDs or LTA1000G are not implemented OR work with errors."),
                            Defered("Down"),
                            Defered("Down")
                        ]
                    )
                ]
            ),
            Category(
                category_id="RCM System Mylib",
                bands=[
                    Band(band_name="mylib", criteria = [
                             Direct("Conform to mylib task and register guidelines [1]"),
                             Empty(),
                             Direct("Some mylib task and register guidelines are not followed [2]"),
                             Empty(),
                             Empty(),
                             Direct("Mylib task and register guides are not followed [3]")
                         ])
                ]
            )
        ],
        description="""
            All movement functions refer to all X, Y, Z, zoom and rotation.

            The below criteria are applied to the mylib.

            1. (Exemplary) And all movement functions work exemplary.
            2. (Competent) Or one or more movement function works competently.
            3. (Absent) Or all movement functions are absent or cannot be compiled.
        """
    ),
    Task(
        task_name="RCM Radio Transmitter",
        categories=[
            Category(
                category_id="2.a/b",
                bands=[
                    Band(
                        band_name="a",
                        criteria=[
                            Direct("Radio Transmitter works correctly."),
                            Defered("up"),
                            Direct("Radio Transmitter works correctly but occasional errors occur."),
                            Defered("up"),
                            Direct("Radio Transmitter works correctly with frequent errors occurring."),
                            Direct("Radio Transmitter is not implemented.")
                        ]
                    ),
                    Band(
                        band_name="b",
                        criteria=[
                            Direct("myconfig.h is correctly used and implemented."),
                            Defered("down"),
                            Defered("down"),
                            Defered("down"),
                            Direct("myconfig.h is not correctly used but correctly implemented."),
                            Direct("myconfig.h is not correctly used or implemented.")
                        ]
                    )
                ]
            ),
            Category(
                category_id="RCM Radio Transmitter Mylib",
                bands=[
                    Band(
                        band_name="mylib",
                        criteria=[
                            Direct("Conform to mylib task and register guidelines [1]"),
                            Empty(),
                            Direct("Some mylib task and register guidelines are not followed [2]"),
                            Empty(),
                            Empty(),
                            Direct("Mylib task and register guides are not followed [3]")
                        ]
                    )
                ]
            )
        ],
        description = ""
    )
])

# Example Usage
if __name__ == "__main__":
    # Example criteria data based on the provided criteria sheet
    # Print example structure
    from pprint import pprint
    pprint(example_criteria)

    from serde.yaml import to_yaml, from_yaml
    print(to_yaml(example_criteria))

    pprint(from_yaml(Criteria, to_yaml((example_criteria))))
