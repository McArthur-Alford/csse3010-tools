import yaml
from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict

@dataclass
class Requirement:
    name: str
    marks: Optional[int] = None
    description: Optional[str] = None
    defers: Optional[str] = None

@dataclass
class Band:
    name: str
    requirements: List[List[Requirement]] = field(default_factory=list)
    keys: List[str] = field(default_factory = list)
    choices: List[int] = field(default_factory = list)
    comment: str = ""
    manual_mark: Optional[int] = None

    def max_marks(self) -> int:
        if len(self.requirements) == 0:
            return 0
        return max([
                   max([
                       req.marks or 0
                       for req in reqs
                   ])
                   if len(reqs) > 0
                   else 0
                   for reqs in self.requirements
               ])

    def get_bounds(self) -> List[tuple[int, int]]:
        result = []
        for (requirements, choice) in zip(self.requirements, self.choices):
            lower = upper = choice

            for i in range(choice + 1, len(requirements), 1):
                if requirements[i].defers == "up":
                    lower = i
                else:
                    break

            for i in range(choice - 1, -1, -1):
                if requirements[i].defers == "down":
                    upper = i
                else:
                    break

            result.append((requirements[upper].marks or 0, requirements[lower].marks or 0))
        return result

    def calculate(self, i: Optional[int] = None, strategy: str = "defered") -> int:
        if self.manual_mark is not None:
            return self.manual_mark

        if not self.requirements:
            return 0

        # Apply the strategy
        if strategy == "defered":
            # Return the smallest upper bound?
            # TODO verify this is the propper approach
            bounds = self.get_bounds()
            if len(bounds) > 0:
                return min([upper for (upper, lower) in bounds])
        return 0

@dataclass
class Task:
    name: str
    description: Optional[str]
    bands: List[Band] = field(default_factory=list)

@dataclass
class Rubric:
    stage: str
    year: str
    semester: str
    tasks: List[Task] = field(default_factory=list)

    def update(self, task, band, subband, mark):
        self.tasks[task].bands[band].choices[subband] = mark

def parse_requirement(raw: Union[str, Dict[str, dict]]) -> Requirement:
    if isinstance(raw, str):
        return Requirement(name=raw)

    if isinstance(raw, dict) and len(raw) == 1:
        req_name = list(raw.keys())[0]
        data = raw[req_name]

        if isinstance(data, dict):
            return Requirement(
                name=req_name,
                marks=data.get("marks"),
                description=data.get("description"),
                defers=data.get("defers")
            )
        elif isinstance(data, str):
            return Requirement(name=req_name, description=data)
        else:
            return Requirement(name=req_name, description=str(data))

    return Requirement(name=str(raw))

def parse_band(d: dict) -> Band:
    name = d["name"]
    raw_requirements = d.get("requirements", [])
    raw_best_of = d.get("multi_requirements", [])
    reqs = None
    keys = []
    if "requirements" in d:
        reqs = [[parse_requirement(item) for item in raw_requirements]]
    else:
        reqs = [[parse_requirement(item) for item in v] for k, v in raw_best_of.items()]
        keys = [k for k, v in raw_best_of.items()]
    choices = [len(req) - 1 for req in reqs]
    return Band(name=name, requirements=reqs, keys=keys, choices=choices)

def parse_task(d: dict) -> Task:
    name = d["name"]
    bands_data = d.get("bands", [])
    bands = [parse_band(b) for b in bands_data]
    description = d.get("description", None)
    return Task(name=name, bands=bands, description=description)

def load_rubric_from_yaml(yaml_str: str) -> Rubric:
    data = yaml.safe_load(yaml_str)
    stage = str(data["stage"])
    year = str(data["year"])
    semester = str(data["semester"])
    tasks_data = data["tasks"]
    tasks = [parse_task(t) for t in tasks_data]
    return Rubric(stage=stage, year=year, semester=semester, tasks=tasks)

def rubric_to_markdown_table(rubric: Rubric) -> str:
    lines = []
    header = "| Mark | Max | DT | Criteria | Comments (CID) |"
    sep = "| ---- | --- | -- | -------- | -------------- |"
    lines.append(header)
    lines.append(sep)

    for task in rubric.tasks:
        for band in task.bands:
            mark = band.calculate()
            mx = band.max_marks()
            tsk = task.name
            # DT (the third column) is unused, so just leave it blank
            lines.append(f"| {mark} | {mx} | {tsk} | {band.name} | {band.comment} |")

    return "\n".join(lines)

def apply_markdown_table_to_rubric(rubric: Rubric, table: str) -> Rubric:
    def find_band_by_name(rubric: Rubric, band_name: str) -> Optional[Band]:
        for task in rubric.tasks:
            for b in task.bands:
                if b.name == band_name:
                    return b
        return None

    lines = table.strip().split('\n')
    # Skip header and separator
    lines = lines[2:]

    for line in lines:
        parts = line.split('|')
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 4:
            continue
        mark_str, max_str, _dt, band_name = parts[:4]
        if not mark_str.isdigit():
            continue
        mark_value = int(mark_str)
        band = find_band_by_name(rubric, band_name)
        if not band:
            continue
        # We just set manual_mark. We do not guess which requirement was chosen.
        band.manual_mark = mark_value

    return rubric

sample_yaml = """
stage: 1
year: 2024
semester: 1
tasks:
  - name: 'Design Task 1: RCM System'
    description: "This task has an optional comment"
    bands:
      - name: Task 1.a/b
        multi_requirements:
          '1.a: Movement Functions':
              - Excellent:
                  marks: 5
                  description: description here
              - Good:
                  marks: 4
                  defers: up
          '1.b: Status LEDs':
              - Excellent:
                  marks: 5
                  defers: down
              - Good:
                  marks: 4
                  description: magical description
  - name: 'Design Task 2: Something Else'
    bands:
      - name: Task 2.a/b
        multi_requirements:
          '2.a: magic':
              - Excellent:
                  marks: 5
                  description: 'A'
          '2.b: sorcery':
              - Excellent:
                  marks: 4
                  description: 'B'
      - name: RCM System MyLib
        requirements:
          - Excellent:
              marks: 5
              description: ugh
"""
example_rubric = load_rubric_from_yaml(sample_yaml)

if __name__ == "__main__":
    rubric = load_rubric_from_yaml(sample_yaml)
    md = rubric_to_markdown_table(rubric)
    print("Initial table:")
    print(md)

    rubric.tasks[0].bands[0].choices = [0, 0]
    rubric.tasks[1].bands[1].choices = [0, 1]
    from pprint import pprint
    pprint(rubric)
    md = rubric_to_markdown_table(rubric)
    print(md)

    # Example of faking a user-provided table to apply:
    user_table = """| Mark | Max | DT | Criteria | Comments (CID) |
| ---- | --- | -- | -------- | -------------- |
| 2 | 3 |  | FooBand |  |
| 5 | 5 |  | BarBand |  |
| 0 | 0 |  | AnExtra |  |
"""
    apply_markdown_table_to_rubric(rubric, user_table)
    print("\nAfter applying user table:")
    print(rubric_to_markdown_table(rubric))
