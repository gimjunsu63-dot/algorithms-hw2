"""Measure separate-chaining probe counts across hash-table load factors."""

from __future__ import annotations

import csv
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hash_table import HashTable


BUCKET_COUNT = 4093
SEED = 20261120
EXPERIMENT_DIR = Path(__file__).resolve().parent
CSV_PATH = EXPERIMENT_DIR / "results.csv"
SVG_PATH = EXPERIMENT_DIR / "results.svg"


@dataclass(frozen=True)
class ExperimentResult:
    target_load_factor: float
    item_count: int
    actual_load_factor: float
    measured_success_average: float
    theoretical_success_average: float
    measured_failure_average: float
    theoretical_failure_average: float


def _random_url(rng: random.Random, domain: str, index: int) -> str:
    token = rng.getrandbits(64)
    return f"https://{domain}.example/{index}/{token:016x}"


def run_experiment() -> list[ExperimentResult]:
    rng = random.Random(SEED)
    results = []

    for quarter_steps in range(1, 17):
        target_load_factor = quarter_steps / 4
        item_count = round(BUCKET_COUNT * target_load_factor)
        table: HashTable[int] = HashTable(bucket_count=BUCKET_COUNT)
        inserted_urls = []

        for index in range(item_count):
            url = _random_url(rng, "inserted", index)
            table.put(url, index)
            inserted_urls.append(url)

        success_comparisons = 0
        for index, url in enumerate(inserted_urls):
            if table.get(url) != index:
                raise RuntimeError(f"successful lookup failed for {url}")
            success_comparisons += table.last_comparisons

        failure_comparisons = 0
        for index in range(item_count):
            url = _random_url(rng, "missing", index)
            if table.get(url) is not None:
                raise RuntimeError(f"failure lookup unexpectedly found {url}")
            failure_comparisons += table.last_comparisons

        actual_load_factor = len(table) / BUCKET_COUNT
        results.append(
            ExperimentResult(
                target_load_factor=target_load_factor,
                item_count=len(table),
                actual_load_factor=actual_load_factor,
                measured_success_average=success_comparisons / item_count,
                theoretical_success_average=1 + actual_load_factor / 2,
                measured_failure_average=failure_comparisons / item_count,
                theoretical_failure_average=actual_load_factor,
            )
        )

    return results


def write_csv(results: list[ExperimentResult]) -> None:
    fieldnames = (
        "target_load_factor",
        "item_count",
        "actual_load_factor",
        "measured_success_average",
        "theoretical_success_average",
        "measured_failure_average",
        "theoretical_failure_average",
    )
    with CSV_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "target_load_factor": f"{result.target_load_factor:.2f}",
                    "item_count": result.item_count,
                    "actual_load_factor": f"{result.actual_load_factor:.6f}",
                    "measured_success_average": (
                        f"{result.measured_success_average:.6f}"
                    ),
                    "theoretical_success_average": (
                        f"{result.theoretical_success_average:.6f}"
                    ),
                    "measured_failure_average": (
                        f"{result.measured_failure_average:.6f}"
                    ),
                    "theoretical_failure_average": (
                        f"{result.theoretical_failure_average:.6f}"
                    ),
                }
            )


def make_svg(results: list[ExperimentResult]) -> str:
    width, height = 960, 600
    left, top, right, bottom = 88, 62, 250, 82
    plot_width = width - left - right
    plot_height = height - top - bottom
    max_value = max(
        result.measured_success_average for result in results
    )
    max_value = max(
        max_value,
        *(result.measured_failure_average for result in results),
        *(result.theoretical_success_average for result in results),
        *(result.theoretical_failure_average for result in results),
    )
    y_max = math.ceil(max_value * 1.1)

    def x_position(load_factor: float) -> float:
        return left + load_factor / 4 * plot_width

    def y_position(value: float) -> float:
        return top + (y_max - value) / y_max * plot_height

    series = (
        (
            "Measured success",
            "measured_success_average",
            "#1f77b4",
            "",
        ),
        (
            "Theory success: 1 + alpha/2",
            "theoretical_success_average",
            "#1f77b4",
            "7 5",
        ),
        (
            "Measured failure",
            "measured_failure_average",
            "#d62728",
            "",
        ),
        (
            "Theory failure: alpha",
            "theoretical_failure_average",
            "#d62728",
            "7 5",
        ),
    )

    elements = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">'
        ),
        '<rect width="100%" height="100%" fill="white"/>',
        (
            f'<text x="{width / 2}" y="30" text-anchor="middle" '
            'font-family="sans-serif" font-size="20">'
            "Average probes vs. load factor</text>"
        ),
    ]

    for tick in range(0, y_max + 1):
        y = y_position(tick)
        elements.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" '
            f'y2="{y:.2f}" stroke="#dddddd"/>'
        )
        elements.append(
            f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" '
            'font-family="sans-serif" font-size="12">'
            f"{tick}</text>"
        )

    for tick in range(0, 9):
        load_factor = tick / 2
        x = x_position(load_factor)
        elements.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
            f'y2="{top + plot_height}" stroke="#eeeeee"/>'
        )
        elements.append(
            f'<text x="{x:.2f}" y="{top + plot_height + 22}" '
            'text-anchor="middle" font-family="sans-serif" font-size="12">'
            f"{load_factor:.1f}</text>"
        )

    elements.extend(
        (
            f'<line x1="{left}" y1="{top}" x2="{left}" '
            f'y2="{top + plot_height}" stroke="#333333"/>',
            f'<line x1="{left}" y1="{top + plot_height}" '
            f'x2="{left + plot_width}" y2="{top + plot_height}" '
            'stroke="#333333"/>',
            (
                f'<text x="{left + plot_width / 2}" y="{height - 24}" '
                'text-anchor="middle" font-family="sans-serif" font-size="14">'
                "Load factor (items / 4093)</text>"
            ),
            (
                f'<text x="22" y="{top + plot_height / 2}" '
                f'transform="rotate(-90 22 {top + plot_height / 2})" '
                'text-anchor="middle" font-family="sans-serif" font-size="14">'
                "Average nodes compared</text>"
            ),
        )
    )

    legend_x = left + plot_width + 28
    for series_index, (label, attribute, color, dash_array) in enumerate(series):
        points = " ".join(
            f"{x_position(result.actual_load_factor):.2f},"
            f"{y_position(getattr(result, attribute)):.2f}"
            for result in results
        )
        dash = f' stroke-dasharray="{dash_array}"' if dash_array else ""
        elements.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="2"{dash}/>'
        )
        for result in results:
            elements.append(
                f'<circle cx="{x_position(result.actual_load_factor):.2f}" '
                f'cy="{y_position(getattr(result, attribute)):.2f}" r="2.5" '
                f'fill="{color}"/>'
            )

        legend_y = top + 20 + series_index * 28
        elements.append(
            f'<line x1="{legend_x}" y1="{legend_y}" '
            f'x2="{legend_x + 28}" y2="{legend_y}" stroke="{color}" '
            f'stroke-width="2"{dash}/>'
        )
        elements.append(
            f'<text x="{legend_x + 36}" y="{legend_y + 4}" '
            'font-family="sans-serif" font-size="12">'
            f"{label}</text>"
        )

    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def print_table(results: list[ExperimentResult]) -> None:
    print(
        "target α | items | actual α | success measured | success theory "
        "| failure measured | failure theory"
    )
    for result in results:
        print(
            f"{result.target_load_factor:8.2f} | {result.item_count:5d} | "
            f"{result.actual_load_factor:8.4f} | "
            f"{result.measured_success_average:16.4f} | "
            f"{result.theoretical_success_average:14.4f} | "
            f"{result.measured_failure_average:16.4f} | "
            f"{result.theoretical_failure_average:14.4f}"
        )


def main() -> None:
    results = run_experiment()
    write_csv(results)
    SVG_PATH.write_text(make_svg(results), encoding="utf-8")
    print_table(results)
    print(f"\nWrote {CSV_PATH}")
    print(f"Wrote {SVG_PATH}")
    print(
        "\nSmall differences from theory are expected: random keys do not "
        "fill every bucket evenly, and the formulas are averages."
    )


if __name__ == "__main__":
    main()
