"""Draw the plan's Gantt chart, gantt.pdf, from the tables at the top of this file.

Edit the tables to match the plan, then run, from any folder:

    python figures/gantt.py

Every time is in weeks from the start of the project, so week 1 runs from 0
to 1 and a task from 0 to 3 fills weeks 1 to 3. A time may be fractional, so
a task can end mid-week. A task that tests a hypothesis takes the colour
\\definebadge gives that hypothesis in main.tex, so the chart, the risk table
and the figures share one key. The script reads laboratory.mplstyle and the
figure helper, laboratory.py, from its own folder.

Raises ValueError, before drawing anything, for two tasks or two marks with one
code; a task or break that does not end after it starts, or that runs outside
weeks 0 to WEEKS; progress given to a work package, or past the status week;
and a milestone or risk outside the chart or on a task that is not in TASKS.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import laboratory as lab
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.text import Annotation


@dataclass(frozen=True, slots=True)
class Task:
    code: str
    name: str
    start_week: float
    end_week: float
    colour: str
    # The work is done up to this week; 0 means none of it is.
    done_until_week: float = 0
    # A work package is drawn as a heading row over the tasks that follow it.
    is_package: bool = False


@dataclass(frozen=True, slots=True)
class Mark:
    code: str
    week: float
    # The code of the task whose row the mark sits on.
    task: str
    label: str = ""


WEEKS = 32
STATUS_WEEK = 0
# Start, end and name of each break, such as a vacation.
BREAKS = ()
TASKS = (
    Task("1", "Harness", 0, 6, lab.INK, is_package=True),
    Task("1.1", "Runner, cache, detection rule", 0, 3, lab.GREY),
    Task("1.2", "First regression end to end", 2, 4, lab.GREY),
    Task("1.3", "Mutation scores for subsets", 4, 6, lab.GREY),
    Task("2", "Feasibility", 0, 10, lab.INK, is_package=True),
    Task("2.1", "Candidate search, licence filter", 0, 3, lab.GREY),
    Task("2.2", "Five candidate regressions", 6, 9, lab.GREY),
    Task("2.3", "Noise floor, power simulation", 8, 10, lab.GREY),
    Task("3", "Corpus", 10, 18, lab.INK, is_package=True),
    Task("3.1", "Reproduce 20 or more regressions", 10, 18, lab.GREY),
    Task("3.2", "Spend and suite sizes checked", 10, 14, lab.GREY),
    Task("4", "Measurements", 18, 24, lab.INK, is_package=True),
    Task("4.1", "Score against detection (H1)", 18, 22, lab.PRUSSIAN),
    Task("4.2", "Coupling (H2)", 20, 23, lab.TERRACOTTA),
    Task("4.3", "Single against repeated runs (H3)", 18, 21, lab.GREY),
    Task("5", "Release and write-up", 24, 32, lab.INK, is_package=True),
    Task("5.1", "Benchmark release", 24, 27, lab.GREY),
    Task("5.2", "Upstream contributions", 24, 29, lab.GREY),
    Task("5.3", "Preprint", 26, 32, lab.GREY),
)
MILESTONES = (
    Mark("MS1", 10, "2", "Analysis plan fixed"),
    Mark("MS2", 18, "3.1", "Corpus frozen"),
    Mark("MS3", 24, "4", "Verdicts"),
    Mark("MS4", 32, "5.1", "Public"),
)
# The weeks the triggers of the plan's risk table fall in.
RISKS = (
    Mark("R1", 3, "2.1"),
    Mark("R2", 9, "2.2"),
    Mark("R3", 10, "2.3"),
    Mark("R4", 12, "3.2"),
    Mark("R5", 14, "3.1"),
    Mark("R6", 19, "4.1"),
)

WIDTH_MM = 150
# Heading and week numbers, then one row per task, so the rows keep their
# height however many tasks there are.
HEAD_MM = 12
ROW_MM = 5.5
BAR_HEIGHT_ROWS = 0.56
PACKAGE_LINE_WIDTH_PT = 2.4
SMALL_TYPE_PT = 8
LABEL_GAP_PT = 6
MARK_LABEL_GAP_PT = 7
PLANNED_TINT = 0.72
PACKAGE_ROW_TINT = 0.94
WEEK_RULE_TINT = 0.88
BREAK_HATCH_TINT = 0.55


def check_tables() -> None:
    """Raise ValueError naming the first entry the chart could not draw faithfully."""
    codes: set[str] = set()
    for task in TASKS:
        if task.code in codes:
            raise ValueError(f"task code {task.code!r} appears twice in TASKS")
        codes.add(task.code)
        _check_span(f"task {task.code}", task.start_week, task.end_week)
        if task.is_package and task.done_until_week:
            raise ValueError(f"task {task.code} is a work package; give its progress to its tasks")
        if task.done_until_week > STATUS_WEEK:
            raise ValueError(
                f"task {task.code} is done to week {task.done_until_week}, "
                f"after the status line at week {STATUS_WEEK}"
            )
    for first, last, name in BREAKS:
        _check_span(f"break {name!r}", first, last)
    mark_codes: set[str] = set()
    for mark in MILESTONES + RISKS:
        if mark.code in mark_codes:
            raise ValueError(f"mark code {mark.code!r} appears twice")
        mark_codes.add(mark.code)
        if mark.task not in codes:
            raise ValueError(f"{mark.code} sits on task {mark.task!r}, which is not in TASKS")
        if not 0 <= mark.week <= WEEKS:
            raise ValueError(f"{mark.code} falls in week {mark.week}, outside weeks 0 to {WEEKS}")


def _check_span(name: str, start_week: float, end_week: float) -> None:
    if end_week <= start_week:
        raise ValueError(
            f"{name} ends in week {end_week}, expected after its start in week {start_week}"
        )
    if start_week < 0 or end_week > WEEKS:
        raise ValueError(
            f"{name} runs from week {start_week} to {end_week}, outside weeks 0 to {WEEKS}"
        )


def draw_rows(axes: Axes) -> None:
    for row, task in enumerate(TASKS):
        if task.is_package:
            band = Rectangle(
                (0, row - 0.5),
                WEEKS,
                1,
                color=lab.tint(lab.INK, PACKAGE_ROW_TINT),
                lw=0,
                zorder=0,
            )
            axes.add_patch(band)
            axes.plot(
                [task.start_week, task.end_week],
                [row, row],
                color=task.colour,
                lw=PACKAGE_LINE_WIDTH_PT,
                solid_capstyle="butt",
                zorder=2,
            )
            continue
        bottom = row - BAR_HEIGHT_ROWS / 2
        planned_weeks = task.end_week - task.start_week
        planned = lab.tint(task.colour, PLANNED_TINT)
        axes.add_patch(
            Rectangle(
                (task.start_week, bottom),
                planned_weeks,
                BAR_HEIGHT_ROWS,
                color=planned,
                lw=0,
                zorder=2,
            )
        )
        done_weeks = min(task.done_until_week, task.end_week) - task.start_week
        if done_weeks > 0:
            axes.add_patch(
                Rectangle(
                    (task.start_week, bottom),
                    done_weeks,
                    BAR_HEIGHT_ROWS,
                    color=task.colour,
                    lw=0,
                    zorder=3,
                )
            )


def draw_calendar(axes: Axes) -> None:
    top = len(TASKS) - 0.35
    for first, last, name in BREAKS:
        hatch = Rectangle(
            (first, -0.5),
            last - first,
            len(TASKS),
            facecolor="none",
            edgecolor=lab.tint(lab.GREY, BREAK_HATCH_TINT),
            hatch="////",
            lw=0,
            zorder=1,
        )
        axes.add_patch(hatch)
        axes.text((first + last) / 2, top, name, ha="center", va="top", color=lab.GREY)
    for week in range(WEEKS + 1):
        axes.axvline(week, color=lab.tint(lab.INK, WEEK_RULE_TINT), lw=0.4, zorder=0.5)
    axes.axvline(STATUS_WEEK, color=lab.INK, lw=0.8, zorder=4)
    axes.annotate(
        f"status, week {STATUS_WEEK}",
        (STATUS_WEEK, top),
        xytext=(4, 0),
        textcoords="offset points",
        va="top",
        color=lab.INK,
    )


def draw_marks(axes: Axes) -> list[Annotation]:
    """Milestones and risk triggers on their tasks' rows; returns the milestone labels."""
    rows = {task.code: row for row, task in enumerate(TASKS)}
    milestone_labels = []
    for mark in MILESTONES:
        row = rows[mark.task]
        axes.plot(
            [mark.week],
            [row],
            marker="D",
            color=lab.INK,
            markersize=5,
            markeredgecolor="white",
            markeredgewidth=0.5,
            zorder=5,
            # A mark in week 0 or the last week sits on the chart's edge.
            clip_on=False,
        )
        label = axes.annotate(
            f"{mark.code} {mark.label}",
            (mark.week, row),
            xytext=(MARK_LABEL_GAP_PT, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=SMALL_TYPE_PT,
            color=lab.INK,
            zorder=6,
        )
        # A label is kept inside the chart, so it must not move the chart to make room.
        label.set_in_layout(False)
        milestone_labels.append(label)
    for mark in RISKS:
        row = rows[mark.task]
        axes.plot(
            [mark.week],
            [row],
            marker="^",
            color="white",
            markersize=5.5,
            markeredgecolor=lab.TERRACOTTA,
            markeredgewidth=0.9,
            zorder=5,
            # A mark in week 0 or the last week sits on the chart's edge.
            clip_on=False,
        )
        axes.annotate(
            mark.code,
            (mark.week, row),
            xytext=(-6, 0),
            textcoords="offset points",
            ha="right",
            va="center",
            fontsize=SMALL_TYPE_PT,
            color=lab.TERRACOTTA,
            family="sans-serif",
            weight="bold",
        )
    return milestone_labels


def label_axes(axes: Axes) -> None:
    axes.set_ylim(len(TASKS) + 0.3, -0.6)
    axes.set_xlim(0, WEEKS)
    axes.set_yticks(range(len(TASKS)), [f"{task.code}  {task.name}" for task in TASKS])
    for label, task in zip(axes.get_yticklabels(), TASKS, strict=True):
        label.set_horizontalalignment("left")
        if task.is_package:
            label.set_fontweight("bold")
    # Each week's number sits in the middle of the week.
    weeks = range(1, WEEKS + 1)
    axes.set_xticks([week - 0.5 for week in weeks], [str(week) for week in weeks])
    axes.xaxis.tick_top()
    axes.tick_params(axis="x", length=0, labelsize=SMALL_TYPE_PT, colors=lab.GREY)
    axes.set_xlabel("week", color=lab.GREY, fontsize=SMALL_TYPE_PT)
    axes.xaxis.set_label_position("top")
    for spine in axes.spines.values():
        spine.set_visible(False)


def hang_task_names(figure: Figure, axes: Axes) -> None:
    """Set the left-aligned task names clear of the chart, however long the longest is."""
    figure.draw_without_rendering()
    widest_px = max(label.get_window_extent().width for label in axes.get_yticklabels())
    widest_pt = widest_px / figure.dpi * lab.POINTS_PER_INCH
    axes.tick_params(axis="y", length=0, pad=widest_pt + LABEL_GAP_PT)


def turn_back_overruns(figure: Figure, axes: Axes, labels: list[Annotation]) -> None:
    """Set a milestone's label left of its mark where it would run past the last week."""
    figure.draw_without_rendering()
    chart_right_px = axes.get_window_extent().x1
    for label in labels:
        if label.get_window_extent().x1 > chart_right_px:
            label.set_horizontalalignment("right")
            # An annotation's position is its text's offset from the mark.
            label.set_position((-MARK_LABEL_GAP_PT, 0))


def draw() -> Figure:
    """The chart, in whatever style and on whatever canvas is current."""
    figure, axes = plt.subplots(figsize=lab.inches(WIDTH_MM, HEAD_MM + ROW_MM * len(TASKS)))
    draw_rows(axes)
    draw_calendar(axes)
    milestone_labels = draw_marks(axes)
    label_axes(axes)
    hang_task_names(figure, axes)
    turn_back_overruns(figure, axes, milestone_labels)
    return figure


def main() -> None:
    check_tables()
    # The pgf canvas sets the labels in the document's faces and measures them as LuaLaTeX does.
    mpl.use("pgf")
    folder = Path(__file__).resolve().parent
    with plt.style.context(folder / "laboratory.mplstyle"):
        figure = draw()
        figure.savefig(folder / "gantt.pdf")
        plt.close(figure)


if __name__ == "__main__":
    main()
