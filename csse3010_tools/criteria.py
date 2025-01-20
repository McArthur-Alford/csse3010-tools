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
    sum_of: Optional[List["Band"]] = None
    best_of: Optional[List["Band"]] = None
    requirements: Optional[List[Requirement]] = None

    # index for the selected requirement
    # increasing index is increasing marks, ALWAYS
    chosen_req: Optional[int] = None

    manual_mark: Optional[int] = None

    def get_bounds(self) -> Optional[tuple[int, int]]:
        if self.requirements is None or self.chosen_req is None:
            return None

        upper = self.chosen_req
        lower = self.chosen_req
        
        # Gets the bounds around the current chosen requirement
        for i in range(self.chosen_req - 1, 0, -1):
            # go down, looking for up-deferals
            if self.requirements[i].defers == "up":
                self.lower = i
            else:
                break

        for i in range(self.chosen_req + 1, len(self.requirements)):
            # go up, looking for down referals
            if self.requirements[i].defers == "down":
                self.upper = i
            else:
                break

        # Calculate marks for the lower and upper bounds
        return (self.calculate(i=lower), self.calculate(i=upper))

    def calculate(self, i: Optional[int] = None) -> int:
        if self.manual_mark is not None:
            return self.manual_mark
        
        value = 0
        if self.sum_of is not None:
            for item in self.sum_of:
                value += item.calculate()
        elif self.best_of is not None:
            # The *boundary* for the selected mark (inclusive):
            bounds = [item.get_bounds() for item in self.best_of]

            # I THINK THAT THE LOWEST UPPER BOUND IS ALWAYS THE HIGHEST POSSIBLE MARK
            mark = None
            for bound in bounds:
                if bound is None:
                    return 0
                (lower, upper) = bound
                if mark is None:
                    mark = upper
                else:
                    mark = min(mark, upper)
            if mark is None:
                return 0
            value = mark
        elif self.requirements is not None:
            index = self.chosen_req
            if i is not None:
                index = i
            if index is None:
                return 0
            temp = self.requirements[index].marks
            if temp is not None:
                value = temp
            else:
                raise ValueError("requirements must have a mark value")
        return value

@dataclass
class Rubric:
    stage: int
    year: int
    semester: int
    tasks: List[Band] = field(default_factory=list)


def parse_requirement(raw: Union[str, Dict[str, dict]]) -> Requirement:
    if isinstance(raw, str):
        return Requirement(name=raw)

    if isinstance(raw, dict) and len(raw) == 1:
        requirement_name = list(raw.keys())[0]
        data = raw[requirement_name]

        if isinstance(data, dict):
            return Requirement(
                name=requirement_name,
                marks=data.get("marks"),
                description=data.get("description"),
                defers=data.get("defers"),
            )
        elif isinstance(data, str):
            return Requirement(
                name=requirement_name,
                description=data
            )
        else:
            return Requirement(name=requirement_name, description=str(data))

    return Requirement(name=str(raw))


def parse_band(d: dict) -> Band:
    name = d["name"]
    
    sub_sum = None
    sub_best = None
    reqs = None

    # Only one can be valid, for my sanity
    if "sum_of" in d:
        sub_sum = [parse_band(x) for x in d["sum_of"]]
    elif "best_of" in d:
        sub_best = [parse_band(x) for x in d["best_of"]]
    elif "requirements" in d:
        raw_requirements = d["requirements"]
        reqs = [parse_requirement(item) for item in raw_requirements]

    return Band(
        name=name,
        sum_of=sub_sum,
        best_of=sub_best,
        requirements=reqs
    )


def load_rubric_from_yaml(yaml_str: str) -> Rubric:
    data = yaml.safe_load(yaml_str)

    stage = data["stage"]
    year = data["year"]
    semester = data["semester"]

    tasks_data = data["tasks"]
    tasks = [parse_band(t) for t in tasks_data]

    return Rubric(
        stage=stage,
        year=year,
        semester=semester,
        tasks=tasks
    )

def apply_markdown_table_to_rubric(rubric: Rubric, markdown_table: str) -> Rubric:
    def find_band_by_name(bands: List[Band], target_name: str) -> Optional[Band]:
        for b in bands:
            if b.name == target_name:
                return b
            # Recurse into sub-bands:
            if b.sum_of:
                sub = find_band_by_name(b.sum_of, target_name)
                if sub:
                    return sub
            if b.best_of:
                sub = find_band_by_name(b.best_of, target_name)
                if sub:
                    return sub
        return None

    lines = markdown_table.strip().split('\n')
    # The first two lines are header and separator:
    # | Mark | Max | DT | Criteria | Comments (CID) |
    # | ---- | --- | -- | -------- | -------------- |
    data_lines = lines[2:]

    for line in data_lines:
        # Each line looks like: "| 0 | 5 |  | Task 1.a/b (Best of a & b) |  |"
        # Split by '|' and strip:
        columns = line.split('|')
        # Typically we get ['', ' 0 ', ' 5 ', '  ', ' Task 1.a/b (Best of a & b) ', '  ', '']
        # so we can slice off the first and last empty pieces:
        columns = columns[1:-1]
        # Now columns should be [' 0 ', ' 5 ', '  ', ' Task 1.a/b (Best of a & b) ', '  ']
        columns = [c.strip() for c in columns]

        if len(columns) < 4:
            # Not a valid row
            continue

        mark_str, _max_str, _dt_str, band_name = columns[:4]
        # We'll ignore the Comments column (if present) for now.
        if not mark_str.isdigit():
            # If 'mark_str' isn't a numeric value (e.g. might be ""), skip.
            continue

        mark_value = int(mark_str)

        # Find the band by its name:
        band = find_band_by_name(rubric.tasks, band_name)
        if not band:
            # No match, skip
            continue

        # If the band has sub-bands (sum_of or best_of), we do NOT set chosen_req,
        # as the table does not provide detail about which sub-requirements were chosen.
        if band.sum_of or band.best_of:
            # We skip, as per the instruction "the sum or best_of blocks are hidden, 
            # they may as well not exist" in terms of picking sub-requirements.
            continue

        # If the band directly has requirements, we attempt to match the mark_value
        if band.requirements:
            # Attempt exact match to a requirement's marks
            for idx, req in enumerate(band.requirements):
                if req.marks == mark_value:
                    band.chosen_req = idx
                    break
            else:
                # If no exact match, do nothing (leave chosen_req=None)
                pass

    return rubric

def rubric_to_markdown_table(rubric: Rubric) -> str:
    def band_max(band: Band) -> int:
        if band.requirements:
            return max(r.marks or 0 for r in band.requirements)
        if band.best_of:
            return max(band_max(b) for b in band.best_of)
        if band.sum_of:
            return sum(band_max(b) for b in band.sum_of)
        return 0

    def band_to_rows(band: Band) -> List[str]:
        rows = []
        mark = band.calculate()
        mx = band_max(band)
        if band.sum_of:
            for sb in band.sum_of:
                rows.extend(band_to_rows(sb))
        else:
            rows.append(f"| {mark} | {mx} |  | {band.name} |  |")
        return rows

    header = "| Mark | Max | DT | Criteria | Comments (CID) |"
    sep = "| ---- | --- | -- | -------- | -------------- |"
    lines = [header, sep]
    for t in rubric.tasks:
        lines.extend(band_to_rows(t))
    return "\n".join(lines)

if __name__ == "__main__":
    sample_yaml = """
stage: 1
year: 2024
semester: 1
tasks:
  - name: "Design Task 1: RCM System"
    sum_of:
      - name: "Task 1.a/b (Best of a & b)"
        best_of:
          - name: "1.a: Movement Functions"
            requirements:
              - Excellent:
                  marks: 5
                  description: "description here"
              - Good:
                  marks: 4
                  defers: "up"
          - name: "1.b: Status LEDs"
            requirements:
              - Excellent:
                  marks: 5
              - Good: "aa"
      - name: "Other Task"
        sum_of:
          - name: "1c"
            requirements:
              - Excellent:
                  marks: 5
                  description: ""
          - name: "1b"
            requirements:
              - Excellent:
                  marks: 4
                  description: ""
      - name: "RCM System MyLib"
        requirements:
          - "d"
"""
    from pprint import pprint

    rubric = load_rubric_from_yaml(sample_yaml)
    pprint(rubric)

    # The name of the first task:
    first_task_name = rubric.tasks[0].name
    print("First task name:", first_task_name)

    # The name of the sub-band in sum_of -> best_of:
    best_of_band_name = rubric.tasks[0].sum_of[0].name
    print("Best-of band:", best_of_band_name)

    # The name+marks of the first requirement under 1.a
    first_req_1a = rubric.tasks[0].sum_of[0].best_of[0].requirements[0]
    print("Requirement name:", first_req_1a.name, "| marks:", first_req_1a.marks)

    md = rubric_to_markdown_table(rubric)
    print(md)

    restored = apply_markdown_table_to_rubric(rubric, md)
    # pprint(restored)
    print(rubric_to_markdown_table(restored))

