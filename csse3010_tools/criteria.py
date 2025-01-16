from typing import List, Union, Optional, Tuple
from dataclasses import dataclass, field
from serde import serde

@serde
@dataclass
class RequirementTypeDeferredUp:
    """Indicates that the requirement is deferred to the next HIGHER mark (up)."""
    pass

@serde
@dataclass
class RequirementTypeDeferredDown:
    """Indicates that the requirement is deferred to the next LOWER mark (down)."""
    pass

@serde
@dataclass
class RequirementTypeDirect:
    """Indicates a text-based requirement."""
    text: str

@serde
@dataclass
class RequirementTypeEmpty:
    """Indicates a blank (unselectable) requirement."""
    pass

RequirementType = Union[
    RequirementTypeDeferredUp,
    RequirementTypeDeferredDown,
    RequirementTypeDirect,
    RequirementTypeEmpty,
]

@serde
@dataclass
class RequirementItem:
    requirement_name: str
    marks: int
    requirement_type: RequirementType

@serde
@dataclass
class Band:
    band_name: str = ""
    description: Optional[str] = None

    def formula(self, marks: List[int]) -> float:
        """
            Computes the marks of this band, given a list of ALREADY COMPUTED
            marks for all sub-items
        """
        return 0.0

@serde
@dataclass
class BaseBand(Band):
    requirements: List[RequirementItem] = field(default_factory=list)

    def formula(self, marks: List[int]) -> float:
        if len(marks) != 1:
            raise ValueError(
                f"BaseBand {self.band_name} expects exactly 1 integer in marks, got {marks}"
            )
        return float(marks[0])

    def valid_range(self, active_index: int) -> Tuple[int, int]:
        if not (0 <= active_index < len(self.requirements)):
            raise ValueError(
                f"BaseBand {self.band_name} expects an index <= {len(self.requirements)}, got {active_index}"
            )

        lower_bound = active_index
        upper_bound = active_index

        for i in range(active_index, 0, -1):
            if self.requirements[i] is RequirementTypeDeferredUp:
                # The item below defers up, so keep going
                lower_bound = i
            else:
                break
        
        for i in range(active_index, len(self.requirements), 1):
            if self.requirements[i] is RequirementTypeDeferredDown:
                # The item above defers down, so keep going
                upper_bound = i
            else:
                break

        return (lower_bound, upper_bound)

@serde
@dataclass
class SummationBand(Band):
    sub_bands: List[Band] = field(default_factory=list)

    def formula(self, marks: List[int]) -> float:
        if len(marks) != len(self.sub_bands):
            raise ValueError(
                f"SummationBand {self.band_name} expects {len(self.sub_bands)} marks, got {len(marks)}"
            )

        return sum(marks)

@serde
@dataclass
class BestBand(Band):
    sub_bands: List[BaseBand] = field(default_factory=list)

    def formula(self, marks: List[int]) -> float:
        if len(marks) != len(self.sub_bands):
            raise ValueError(
                f"BestBand {self.band_name} expects {len(self.sub_bands)} marks, got {len(marks)}"
            )

        # The mark is the lowest upper bound, effectively
        # TODO verify this with matt, and some experiments
        mark = 0
        for band, single_mark in zip(self.sub_bands, marks):
            # Get the valid range around the mark that the sub-band allows
            (lower, upper) = band.valid_range(single_mark)

            # Get the maximum Possible Mark
            mark = max(mark, upper)

        return mark

@serde
@dataclass
class Rubric:
    year: str
    semester: str
    stage: str
    tasks: SummationBand # Rubric is always a sum of bands

@serde
@dataclass
class MarkedBand:
    band_name: str = ""
    mark: int = 0

@serde
@dataclass
class MarkedRubric:
    year: str
    semester: str
    stage: str
    tasks: str = "MarkedSummationBand"
    global_comment: str = ""


rubric = Rubric(
    year="2025",
    semester="1",
    stage="3",
    tasks=SummationBand(
        band_name="All RCM Tasks",
        sub_bands=[
            SummationBand(
                band_name="Design Task 1: RCM System (10 Marks)",
                sub_bands=[
                    BestBand(
                        band_name="Task 1.a/b (Best of a & b)",
                        sub_bands=[
                            BaseBand(
                                band_name="1.a: Movement Functions",
                                requirements=[
                                    RequirementItem(
                                        requirement_name="Absent",
                                        marks=0,
                                        requirement_type=RequirementTypeDirect(
                                            "None of the movement functions work."
                                        ),
                                    ),
                                    RequirementItem(
                                        requirement_name="Inadequate",
                                        marks=1,
                                        requirement_type=RequirementTypeDeferredUp(),
                                    ),
                                    RequirementItem(
                                        requirement_name="Insufficient",
                                        marks=2,
                                        requirement_type=RequirementTypeDirect(
                                            "More than half the movement functions are implemented and work with no errors."
                                        ),
                                    ),
                                    RequirementItem(
                                        requirement_name="Competent",
                                        marks=3,
                                        requirement_type=RequirementTypeDeferredUp(),
                                    ),
                                    RequirementItem(
                                        requirement_name="Proficient",
                                        marks=4,
                                        requirement_type=RequirementTypeDirect(
                                            "All movement functions fully work with minimal errors."
                                        ),
                                    ),
                                    RequirementItem(
                                        requirement_name="Exemplary",
                                        marks=5,
                                        requirement_type=RequirementTypeDirect(
                                            "All movement functions fully work without errors."
                                        ),
                                    ),
                                ],
                            ),
                            BaseBand(
                                band_name="1.b: Status LEDs / LTA1000G",
                                requirements=[
                                    RequirementItem(
                                        requirement_name="Absent (0)",
                                        marks=0,
                                        requirement_type=RequirementTypeDirect(
                                            "Status LEDs / LTA1000G not functioning."
                                        ),
                                    ),
                                    RequirementItem(
                                        requirement_name="Inadequate (1)",
                                        marks=1,
                                        requirement_type=RequirementTypeDeferredUp(),
                                    ),
                                    RequirementItem(
                                        requirement_name="Insufficient (2)",
                                        marks=2,
                                        requirement_type=RequirementTypeDirect(
                                            "Status LEDs / LTA1000G partially implemented but with errors."
                                        ),
                                    ),
                                    RequirementItem(
                                        requirement_name="Competent (3)",
                                        marks=3,
                                        requirement_type=RequirementTypeDeferredDown(),
                                    ),
                                    RequirementItem(
                                        requirement_name="Proficient (4)",
                                        marks=4,
                                        requirement_type=RequirementTypeDirect(
                                            "Status LEDs / LTA1000G work with minor issues."
                                        ),
                                    ),
                                    RequirementItem(
                                        requirement_name="Exemplary (5)",
                                        marks=5,
                                        requirement_type=RequirementTypeDirect(
                                            "Status LEDs / LTA1000G fully operational with no errors."
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    BaseBand(
                        band_name="RCM System MyLib",
                        requirements=[
                            RequirementItem(
                                requirement_name="Absent (0)",
                                marks=0,
                                requirement_type=RequirementTypeDirect(
                                    "Mylib task and register guides are not followed."
                                ),
                            ),
                            RequirementItem(
                                requirement_name="Inadequate (1)",
                                marks=1,
                                requirement_type=RequirementTypeEmpty(),
                            ),
                            RequirementItem(
                                requirement_name="Insufficient (2)",
                                marks=2,
                                requirement_type=RequirementTypeEmpty(),
                            ),
                            RequirementItem(
                                requirement_name="Competent (3)",
                                marks=3,
                                requirement_type=RequirementTypeDirect(
                                    "Some mylib task/register guidelines not followed."
                                ),
                            ),
                            RequirementItem(
                                requirement_name="Proficient (4)",
                                marks=4,
                                requirement_type=RequirementTypeEmpty(),
                            ),
                            RequirementItem(
                                requirement_name="Exemplary (5)",
                                marks=5,
                                requirement_type=RequirementTypeDirect(
                                    "Conform to mylib task and register guidelines."
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            BaseBand(
                band_name="Design Task 2: RCM Radio Transmitter (5 Marks)",
                requirements=[
                    RequirementItem(
                        requirement_name="Absent (0)",
                        marks=0,
                        requirement_type=RequirementTypeDirect(
                            "Radio Transmitter is not implemented. myconfig.h not used."
                        ),
                    ),
                    RequirementItem(
                        requirement_name="Inadequate (1)",
                        marks=1,
                        requirement_type=RequirementTypeDirect(
                            "Radio Transmitter works with frequent errors; myconfig.h is incorrect."
                        ),
                    ),
                    RequirementItem(
                        requirement_name="Insufficient (2)",
                        marks=2,
                        requirement_type=RequirementTypeDirect(
                            "Radio Transmitter works but has issues; myconfig.h partially correct."
                        ),
                    ),
                    RequirementItem(
                        requirement_name="Competent (3)",
                        marks=3,
                        requirement_type=RequirementTypeDirect(
                            "Radio Transmitter works correctly with occasional errors; myconfig.h is correct."
                        ),
                    ),
                    RequirementItem(
                        requirement_name="Proficient (4)",
                        marks=4,
                        requirement_type=RequirementTypeDirect(
                            "Radio Transmitter works reliably; myconfig.h is properly used."
                        ),
                    ),
                    RequirementItem(
                        requirement_name="Exemplary (5)",
                        marks=5,
                        requirement_type=RequirementTypeDirect(
                            "Radio Transmitter fully correct with no errors; myconfig.h fully compliant."
                        ),
                    ),
                ],
            ),
        ],
    ),
)

if __name__ == "__main__":
    from pprint import pprint
    pprint(rubric)

    from serde.yaml import to_yaml, from_yaml
    print(to_yaml(rubric))

    pprint(from_yaml(Rubric, to_yaml(rubric)))

# # Example criteria from project
# example_criteria = Criteria(
#     year="2024", 
#     semester="1", 
#     stage="0", 
#     tasks=[
#     Task(
#         task_name="RCM System",
#         categories=[
#             Category(
#                 category_id="1.a/b",
#                 bands=[
#                     Band(
#                         band_name="a",
#                         criteria=[
#                             Direct("All movement functions fully work without errors."),
#                             Defered("Up"),
#                             Direct("All movement functions are implemented but errors occur."),
#                             Direct("More than half the movement functions are implemented and work with no errors."),
#                             Direct("Less than half the movement functions are implemented and at least partially work."),
#                             Direct("None of the movement functions work")
#                         ]
#                     ),
#                     Band(
#                         band_name="b",
#                         criteria=[
#                             Direct("Status LEDs and LTA1000G work correctly."),
#                             Defered("Down"),
#                             Defered("Down"),
#                             Direct("Status LEDs or LTA1000G are not implemented OR work with errors."),
#                             Defered("Down"),
#                             Defered("Down")
#                         ]
#                     )
#                 ]
#             ),
#             Category(
#                 category_id="RCM System Mylib",
#                 bands=[
#                     Band(band_name="mylib", criteria = [
#                              Direct("Conform to mylib task and register guidelines [1]"),
#                              Empty(),
#                              Direct("Some mylib task and register guidelines are not followed [2]"),
#                              Empty(),
#                              Empty(),
#                              Direct("Mylib task and register guides are not followed [3]")
#                          ])
#                 ]
#             )
#         ],
#         description="""
#             All movement functions refer to all X, Y, Z, zoom and rotation.

#             The below criteria are applied to the mylib.

#             1. (Exemplary) And all movement functions work exemplary.
#             2. (Competent) Or one or more movement function works competently.
#             3. (Absent) Or all movement functions are absent or cannot be compiled.
#         """
#     ),
#     Task(
#         task_name="RCM Radio Transmitter",
#         categories=[
#             Category(
#                 category_id="2.a/b",
#                 bands=[
#                     Band(
#                         band_name="a",
#                         criteria=[
#                             Direct("Radio Transmitter works correctly."),
#                             Defered("up"),
#                             Direct("Radio Transmitter works correctly but occasional errors occur."),
#                             Defered("up"),
#                             Direct("Radio Transmitter works correctly with frequent errors occurring."),
#                             Direct("Radio Transmitter is not implemented.")
#                         ]
#                     ),
#                     Band(
#                         band_name="b",
#                         criteria=[
#                             Direct("myconfig.h is correctly used and implemented."),
#                             Defered("down"),
#                             Defered("down"),
#                             Defered("down"),
#                             Direct("myconfig.h is not correctly used but correctly implemented."),
#                             Direct("myconfig.h is not correctly used or implemented.")
#                         ]
#                     )
#                 ]
#             ),
#             Category(
#                 category_id="RCM Radio Transmitter Mylib",
#                 bands=[
#                     Band(
#                         band_name="mylib",
#                         criteria=[
#                             Direct("Conform to mylib task and register guidelines [1]"),
#                             Empty(),
#                             Direct("Some mylib task and register guidelines are not followed [2]"),
#                             Empty(),
#                             Empty(),
#                             Direct("Mylib task and register guides are not followed [3]")
#                         ]
#                     )
#                 ]
#             )
#         ],
#         description = ""
#     )
# ])

# # Example Usage
# if __name__ == "__main__":
#     # Example criteria data based on the provided criteria sheet
#     # Print example structure
#     from pprint import pprint
#     pprint(example_criteria)

#     from serde.yaml import to_yaml, from_yaml
#     print(to_yaml(example_criteria))

#     pprint(from_yaml(Criteria, to_yaml((example_criteria))))
