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
    requirements: Dict[str, Dict[int, Requirement]] = field(default_factory=dict)
    chosen_marks: Dict[str, int] = field(default_factory=dict)
    comment: str = ""
    manual_mark: Optional[int] = None

    def max_marks(self) -> int:
        if not self.requirements:
            return 0
        max_marks = max([
            max([(req.marks or 0) for req in marks_dict.values()])
            for marks_dict in self.requirements.values()
        ])
        return max_marks

    def min_marks(self) -> int:
        if not self.requirements:
            return 0
        return min([
            min((req.marks or 0) for req in marks_dict.values())
            for marks_dict in self.requirements.values()
        ])

    def headings(self) -> Dict[int | None, str]:
        out = {}
        for req in self.requirements.values():
            for key, value in req.items():
                out[value.marks] = value.name
        return out

    def get_bounds(self) -> List[tuple[int, int]]:
        result = []
        for subband, marks_dict in self.requirements.items():
            chosen_mark = 0
            if subband in self.chosen_marks:
                chosen_mark = self.chosen_marks[subband]

            lower = chosen_mark
            upper = chosen_mark

            # Selected an unspecified mark, just assume its a single thing
            if chosen_mark not in marks_dict:
                result.append((lower, upper))
                continue

            # Account for a deferal being selected directly
            if marks_dict[chosen_mark].defers == "up":
                upper += 1
            elif marks_dict[chosen_mark].defers == "down":
                lower -= 1
            
            # expand the bounds until we stop hitting deferals (or out of bounds)
            for i in range(chosen_mark+1, self.max_marks()+1, 1):
                if i not in marks_dict:
                    break
                req = marks_dict[i]
                if req.defers == "down":
                    upper += 1
                else:
                    break

            for i in range(chosen_mark-1, self.min_marks()-1, -1):
                if i not in marks_dict:
                    break
                req = marks_dict[i]
                if req.defers == "up":
                    lower -= 1
                else:
                    break

            result.append((lower, upper))
        return result

    def calculate(self, i: Optional[int] = None, strategy: str = "defered") -> int:
        if self.manual_mark is not None:
            return self.manual_mark
        if not self.requirements:
            return 0
        if strategy == "defered":
            bounds = self.get_bounds()
            if len(bounds) > 0:
                return min([upper for (lower, upper) in bounds])
        return 0

@dataclass
class Task:
    name: str
    description: Optional[str]
    bands: List[Band] = field(default_factory=list)

    def marks(self) -> int:
        return sum([band.calculate() for band in self.bands])

    def max_marks(self) -> int:
        return sum([band.max_marks() for band in self.bands])

@dataclass
class Rubric:
    stage: str
    year: str
    semester: str
    tasks: List[Task] = field(default_factory=list)

    def update(self, task, band, subband, mark):
        self.tasks[task].bands[band].chosen_marks[subband] = mark

    def marks(self) -> int:
        return sum([task.marks() for task in self.tasks])

    def max_marks(self) -> int:
        return sum([task.max_marks() for task in self.tasks])

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
    b = Band(name=name)
    if "requirements" in d:
        subband_name = "default"
        b.requirements[subband_name] = {}
        marks_in_order = []
        for item in d["requirements"]:
            req = parse_requirement(item)
            b.requirements[subband_name][req.marks or 0] = req
            marks_in_order.append(req.marks or 0)
        if marks_in_order:
            b.chosen_marks[subband_name] = marks_in_order[-1]
    else:
        raw_best_of = d.get("multi_requirements", {})
        for subband_name, items in raw_best_of.items():
            b.requirements[subband_name] = {}
            marks_in_order = []
            for item in items:
                req = parse_requirement(item)
                b.requirements[subband_name][req.marks or 0] = req
                marks_in_order.append(req.marks or 0)
            if marks_in_order:
                b.chosen_marks[subband_name] = marks_in_order[-1]
    return b

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

    from pprint import pprint
    pprint(rubric)
    md = rubric_to_markdown_table(rubric)
    print(md)

    rubric.tasks[0].bands[0].chosen_marks["1.a: Movement Functions"] = 0
    rubric.tasks[0].bands[0].chosen_marks["1.b: Status LEDs"] = 0
    rubric.tasks[1].bands[1].chosen_marks["default"] = 0

    # After Changes:
    print("\nAfter changes:")
    print(rubric_to_markdown_table(rubric))

#     user_table = """| Mark | Max | DT | Criteria | Comments (CID) |
# | ---- | --- | -- | -------- | -------------- |
# | 2 | 5 |  | Design Task 1: RCM System | Task 1.a/b |
# | 5 | 5 |  | Design Task 2: Something Else | Task 2.a/b |
# | 8 | 5 |  | Design Task 2: Something Else | RCM System MyLib |
# """

    # After reapplying the table:
    apply_markdown_table_to_rubric(rubric, md)
    print("\nAfter applying user table:")
    print(rubric_to_markdown_table(rubric))
