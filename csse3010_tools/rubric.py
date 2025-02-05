from typing import List, Dict, DefaultDict, Self
from types import NotImplementedType
from serde import serialize, deserialize, yaml, serde, field
from serde.yaml import from_yaml, to_yaml
from dataclasses import dataclass


def common_entries(*dcts):
    if not dcts:
        return
    for i in set(dcts[0]).intersection(*dcts[1:]):
        yield (i,) + tuple(d[i] for d in dcts)


@serde
class Band:
    # results maps mark to description
    descriptions: Dict[int, str] = field(default_factory=DefaultDict)

    # the chosen mark
    choice: int = field(default=0, skip=True)
    override: int | None = field(default=None, skip=True)

    def calc_marks(self) -> float:
        return float(self.choice)

    def max_marks(self) -> int:
        m = 0
        for result in self.descriptions.keys():
            m = max(m, result)
        return m

    def min_marks(self) -> int:
        return min([key for key in self.descriptions.keys()])

    def __eq__(self, other: object) -> bool | NotImplementedType:
        if not isinstance(other, Band):
            return NotImplemented

        return self.descriptions == other.descriptions and self.choice == other.choice


@serde
class Task:
    description: str = ""
    comment: str = field(default="", skip=True)

    # headings maps mark to heading (excellent, absent, etc)
    headings: Dict[int, str] = field(default_factory=DefaultDict)

    # Maps CID to band (e.g. a, b, c, d, etc)
    bands: Dict[str, Band] = field(default_factory=DefaultDict)

    def __post_init__(self):
        headings = object.__getattribute__(self, "headings")
        object.__setattr__(
            self,
            "headings",
            {
                0: "Absent",
                1: "Inadequate",
                2: "Insufficient",
                3: "Competent",
                4: "Proficient",
                5: "Exemplary",
            }
            | headings,
        )

    def calc_marks(self) -> float:
        sum = 0.0
        for b in self.bands.values():
            sum += b.calc_marks()
        return sum / float(len(self.bands))

    def max_marks(self) -> int:
        marks = 0
        for b in self.bands.values():
            marks = max(marks, b.max_marks())
        return marks

    def min_marks(self) -> int | None:
        marks = None
        for b in self.bands.values():
            if marks is None:
                marks = b.min_marks()
            else:
                marks = min(marks, b.min_marks())
        return marks

    def __eq__(self, other: object) -> bool | NotImplementedType:
        if not isinstance(other, Task):
            return NotImplemented

        return (
            self.description == other.description
            and self.comment == other.comment
            and self.headings == other.headings
            and self.bands == other.bands
        )


@serde
class Rubric:
    year: str
    sem: str
    name: str
    yaml: str = field(default="")
    tasks: Dict[str, Task] = field(default_factory=DefaultDict)

    @classmethod
    def from_file(cls, path: str) -> Self:
        with open(path) as f:
            return Rubric.from_yaml(f.read())  # type: ignore[return-value]

    @classmethod
    def from_yaml(cls, yaml: str) -> Self:
        rubric = from_yaml(Rubric, yaml)
        rubric.yaml = yaml
        return rubric  # type: ignore[return-value]

    def write_file(self, path: str):
        with open(path, "w") as f:
            f.write(self.into_md())

    def calc_marks(self) -> float:
        return sum([b.calc_marks() for b in self.tasks.values()])

    def max_marks(self) -> int:
        return sum([b.max_marks() for b in self.tasks.values()])

    def load_md(self, md: str):
        lines = md.strip().split("\n")
        if not lines:
            return  # Nothing to parse

        # 1) Find the header line that starts with '| cid'
        header_idx = None
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("| cid"):
                header_idx = i
                break

        if header_idx is None:
            # No recognizable header found, nothing to load
            return

        # 2) Parse the header line to get the column names
        header_line = lines[header_idx].strip()
        header_cells = [c.strip() for c in header_line.split("|") if c.strip()]
        # Example: header_cells might look like ['cid', 'dt1', 'dt2', 'mylib']

        # The first cell should be 'cid', and the rest are the task descriptions
        if not header_cells or header_cells[0].lower() != "cid":
            return
        task_names = header_cells[1:]  # everything after 'cid'

        # 3) Create a map from task name -> Task object (for quick lookup)
        task_map = {}
        for k, t in self.tasks.items():
            task_map[k] = t

        # 4) Skip the alignment line (the next line after the header)
        data_start_idx = header_idx + 2

        # 5) Process the data rows
        for row_idx in range(data_start_idx, len(lines)):
            line = lines[row_idx].strip()
            if not line.startswith("|"):
                # No longer in table rows
                break

            # Split by '|' and strip
            row_cells = [c.strip() for c in line.split("|") if c.strip()]

            # If there are not enough cells, skip
            if len(row_cells) < 2:
                continue

            # The first cell is either 'avg.' or something like 'a.', 'b.', etc.
            cid_cell = row_cells[0].lower()
            if cid_cell.startswith("avg"):
                # This is the 'avg.' row. We ignore it.
                continue

            # The first cell may also be comment
            comment_cell = row_cells[0].lower()

            # Otherwise, parse out the band key. Usually it's 'a.', 'b.', etc.
            band_key = cid_cell.rstrip(".")

            # We expect the subsequent cells to match up with the task_names
            # e.g. row_cells[1] => task_names[0], row_cells[2] => task_names[1], ...
            for col_idx, cell_val in enumerate(row_cells[1:]):
                if col_idx >= len(task_names):
                    break  # More columns than we have tasks, oops

                task_name = task_names[col_idx]
                # Find the corresponding Task object
                task_obj = task_map.get(task_name)
                if not task_obj:
                    # The Markdown had a column for a task name we don't have;
                    # skip it or optionally create it. We'll skip here.
                    continue

                if comment_cell.startswith("comment"):
                    task_obj.comment = cell_val
                    continue

                # If the cell is '-', skip updating
                if cell_val == "-":
                    continue

                # Attempt to parse the cell as a float
                try:
                    chosen_val = int(cell_val)
                except ValueError:
                    # If it fails, skip (or default to 0)
                    continue

                # Ensure the band exists in this task
                if band_key not in task_obj.bands:
                    task_obj.bands[band_key] = Band()

                # Update the chosen mark
                task_obj.bands[band_key].choice = chosen_val

    def into_md(self) -> str:
        # 1) Collect all task names in order
        task_names = [task for task in self.tasks.keys()]

        # 2) Collect all band keys from all tasks
        all_bands = set()
        for task in self.tasks.values():
            for band_key in task.bands.keys():
                all_bands.add(band_key)
        sorted_bands = sorted(all_bands)

        # If there are no tasks, return an empty string
        if not self.tasks:
            return ""

        # 3) Build the header row
        header_cells = ["cid"] + task_names
        header_row = "| " + " | ".join(header_cells) + " |\n"

        # 4) Build the alignment row (Markdown alignment syntax)
        align_row = "| " + " | ".join(["--"] * len(header_cells)) + " |\n"

        # 5) Build the rows for each band key
        data_rows = []
        for bkey in sorted_bands:
            row_cells = [f"{bkey}."]  # The first cell is something like 'a.', 'b.' etc.
            # For each task, show the chosen value if present, else '-'
            for t in self.tasks.values():
                band = t.bands.get(bkey)
                if band is not None:
                    row_cells.append(str(band.choice))
                else:
                    row_cells.append("-")
            data_rows.append("| " + " | ".join(row_cells) + " |\n")

        # 6) Build the average row
        avg_cells = ["avg."]
        for t in self.tasks.values():
            # collect all chosen values from the bands
            chosen_values = [band.choice for band in t.bands.values()]
            if chosen_values:
                avg_val = sum(chosen_values) / len(chosen_values)
                # Format to one decimal place (you can adjust as you wish)
                avg_cells.append(str(round(avg_val, 1)))
            else:
                avg_cells.append("-")
        avg_row = "| " + " | ".join(avg_cells) + " |\n"

        # 7) Build the comments row
        comment_cells = ["comments"]
        for t in self.tasks.values():
            comment = t.comment
            comment_cells.append(comment)
        comment_row = "| " + " | ".join(comment_cells) + " |\n"

        # 8) Combine everything into a single string
        table_md = header_row + align_row + "".join(data_rows) + avg_row + comment_row
        return table_md

    def load_yaml(self, yaml: str):
        self.tasks = {}
        rubric = from_yaml(Rubric, yaml)
        self.yaml = yaml
        self.tasks = rubric.tasks

    def into_yaml(self):
        return to_yaml(self)

    def __eq__(self, other: object) -> bool | NotImplementedType:
        if not isinstance(other, Rubric):
            return NotImplemented

        for task, other_task in zip(self.tasks, other.tasks):
            if task != other_task:
                return False

        # Done recursing, just have to check fields:
        return (
            self.year == other.year
            and self.sem == other.sem
            and self.name == other.name
        )

    def compare_md(self, md: str) -> bool:
        rubric2: Rubric = Rubric.from_yaml(self.yaml)
        rubric2.load_md(md)
        return self.yaml == rubric2.yaml and self == rubric2

    def update_mark(self, task_name: str, band_name: str, chosen_mark: int) -> None:
        self.tasks[task_name].bands[band_name].choice = chosen_mark

    def update_comment(self, task_name: str, comment: str) -> None:
        self.tasks[task_name].comment = comment


if __name__ == "__main__":
    rubric = Rubric(
        year="2024",
        sem="1",
        name="pf",
        tasks={
            "dt1": Task(
                description="description",
                comment="comment",
                headings={0: "magic"},
                bands={
                    "a": Band(
                        descriptions={0: "Very good stuff overall"},
                        choice=0,
                    )
                },
            ),
            "dt2": Task(
                description="This is dt2",
                comment="Slightly buggy",
                bands={
                    "a": Band(descriptions={0: "Absent", 1: "Ok", 2: "Excellent"}),
                    "b": Band(
                        descriptions={0: "Absent", 1: "Ok", 2: "Excellent"}, choice=1
                    ),
                },
            ),
        },
    )

    from pprint import pprint

    pprint(rubric)

    md = rubric.into_md()
    print(md)

    rubric.tasks["dt1"].bands["a"].choice = 4
    rubric.tasks["dt2"].bands["b"].choice = 4
    rubric.tasks["dt2"].comment = "yeet"

    print(rubric.into_md())

    rubric.load_md(md)
    print(rubric.into_md())

    print(rubric.into_yaml())

    path = "./criteria/pf.yaml"
    yaml_string = ""
    with open(path, "r") as f:
        yaml_string = f.read()
    new_rubric = Rubric.from_yaml(yaml_string)

    print(new_rubric.into_md())

    print(new_rubric == new_rubric)

    print(new_rubric.compare_md(new_rubric.into_md()))
