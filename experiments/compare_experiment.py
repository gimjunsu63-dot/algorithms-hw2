"""Compare separate chaining and linear probing across load factors."""

from __future__ import annotations

import csv
import random
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hash_table import HashTable
from linear_probing import LinearProbingTable


BUCKET_COUNT = 4093
SEED = 20261120
EXPERIMENT_DIR = Path(__file__).resolve().parent
CSV_PATH = EXPERIMENT_DIR / "compare_results.csv"
SVG_PATH = EXPERIMENT_DIR / "compare_results.svg"
LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))


@dataclass(frozen=True)
class TableResult:
    measured_success_average: float
    theoretical_success_average: float
    measured_failure_average: float
    theoretical_failure_average: float


@dataclass(frozen=True)
class ExperimentResult:
    target_load_factor: float
    item_count: int
    actual_load_factor: float
    chaining: TableResult
    linear: TableResult


def _random_url(rng: random.Random, namespace: str, index: int) -> str:
    token = rng.getrandbits(64)
    return f"https://{namespace}.example/{index}/{token:016x}"


def _measure(
    table: HashTable[int] | LinearProbingTable[int],
    inserted_urls: list[str],
    missing_urls: list[str],
) -> tuple[float, float]:
    success_comparisons = 0
    for index, url in enumerate(inserted_urls):
        if table.get(url) != index:
            raise RuntimeError(f"successful lookup failed for {url}")
        success_comparisons += table.last_comparisons

    failure_comparisons = 0
    for url in missing_urls:
        if table.get(url) is not None:
            raise RuntimeError(f"failure lookup unexpectedly found {url}")
        failure_comparisons += table.last_comparisons

    return (
        success_comparisons / len(inserted_urls),
        failure_comparisons / len(missing_urls),
    )


def run_experiment() -> list[ExperimentResult]:
    rng = random.Random(SEED)
    max_item_count = round(BUCKET_COUNT * LOAD_FACTORS[-1])
    inserted_urls = [
        _random_url(rng, "inserted", index) for index in range(max_item_count)
    ]
    missing_urls = [
        _random_url(rng, "missing", index) for index in range(max_item_count)
    ]
    results = []

    for target_load_factor in LOAD_FACTORS:
        item_count = round(BUCKET_COUNT * target_load_factor)
        current_inserted_urls = inserted_urls[:item_count]
        current_missing_urls = missing_urls[:item_count]
        chaining: HashTable[int] = HashTable(bucket_count=BUCKET_COUNT)
        linear: LinearProbingTable[int] = LinearProbingTable(
            bucket_count=BUCKET_COUNT
        )

        for index, url in enumerate(current_inserted_urls):
            chaining.put(url, index)
            linear.put(url, index)

        if len(chaining) != item_count or len(linear) != item_count:
            raise RuntimeError("a table did not store every generated URL")

        chaining_success, chaining_failure = _measure(
            chaining, current_inserted_urls, current_missing_urls
        )
        linear_success, linear_failure = _measure(
            linear, current_inserted_urls, current_missing_urls
        )
        actual_load_factor = item_count / BUCKET_COUNT

        results.append(
            ExperimentResult(
                target_load_factor=target_load_factor,
                item_count=item_count,
                actual_load_factor=actual_load_factor,
                chaining=TableResult(
                    measured_success_average=chaining_success,
                    theoretical_success_average=1 + actual_load_factor / 2,
                    measured_failure_average=chaining_failure,
                    theoretical_failure_average=actual_load_factor,
                ),
                linear=TableResult(
                    measured_success_average=linear_success,
                    theoretical_success_average=0.5
                    * (1 + 1 / (1 - actual_load_factor)),
                    measured_failure_average=linear_failure,
                    theoretical_failure_average=0.5
                    * (1 + 1 / (1 - actual_load_factor) ** 2),
                ),
            )
        )

    return results


def write_csv(results: list[ExperimentResult]) -> None:
    fieldnames = (
        "target_load_factor",
        "item_count",
        "actual_load_factor",
        "table",
        "measured_success_average",
        "theoretical_success_average",
        "measured_failure_average",
        "theoretical_failure_average",
    )
    with CSV_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for result in results:
            for table_name in ("chaining", "linear"):
                table_result = getattr(result, table_name)
                writer.writerow(
                    {
                        "target_load_factor": f"{result.target_load_factor:.1f}",
                        "item_count": result.item_count,
                        "actual_load_factor": f"{result.actual_load_factor:.6f}",
                        "table": table_name,
                        "measured_success_average": (
                            f"{table_result.measured_success_average:.6f}"
                        ),
                        "theoretical_success_average": (
                            f"{table_result.theoretical_success_average:.6f}"
                        ),
                        "measured_failure_average": (
                            f"{table_result.measured_failure_average:.6f}"
                        ),
                        "theoretical_failure_average": (
                            f"{table_result.theoretical_failure_average:.6f}"
                        ),
                    }
                )


def make_svg(results: list[ExperimentResult]) -> str:
    width, height = 1180, 660
    plot_width = 460
    plot_top, plot_bottom = 150, 560
    plot_height = plot_bottom - plot_top
    panel_lefts = (90, 660)
    table_series = (
        ("chaining", "Chaining", "#1f77b4"),
        ("linear", "Linear probing", "#ff7f0e"),
    )

    elements = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">'
        ),
        '<rect width="100%" height="100%" fill="white"/>',
        (
            f'<text x="{width / 2}" y="32" text-anchor="middle" '
            'font-family="sans-serif" font-size="21">'
            "Measured and theoretical average comparisons</text>"
        ),
    ]

    legend_items = (
        ("Chaining measured", "#1f77b4", ""),
        ("Chaining theory", "#1f77b4", "7 5"),
        ("Linear measured", "#ff7f0e", ""),
        ("Linear theory", "#ff7f0e", "7 5"),
    )
    for index, (label, color, dash_array) in enumerate(legend_items):
        legend_x = 74 + index * 275
        dash = f' stroke-dasharray="{dash_array}"' if dash_array else ""
        elements.append(
            f'<line x1="{legend_x}" y1="76" x2="{legend_x + 28}" y2="76" '
            f'stroke="{color}" stroke-width="2"{dash}/>'
        )
        elements.append(
            f'<text x="{legend_x + 36}" y="80" font-family="sans-serif" '
            f'font-size="12">{label}</text>'
        )

    for panel_index, probe_type in enumerate(("success", "failure")):
        left = panel_lefts[panel_index]
        measured_attribute = f"measured_{probe_type}_average"
        theoretical_attribute = f"theoretical_{probe_type}_average"
        max_value = max(
            getattr(getattr(result, table_name), attribute)
            for result in results
            for table_name, _, _ in table_series
            for attribute in (measured_attribute, theoretical_attribute)
        )
        y_max = max_value * 1.1

        def x_position(load_factor: float) -> float:
            return left + load_factor * plot_width

        def y_position(value: float) -> float:
            return plot_top + (y_max - value) / y_max * plot_height

        elements.append(
            f'<text x="{left + plot_width / 2}" y="120" text-anchor="middle" '
            'font-family="sans-serif" font-size="16">'
            f"{probe_type.capitalize()} searches</text>"
        )

        for tick in range(6):
            value = y_max * tick / 5
            y = y_position(value)
            elements.append(
                f'<line x1="{left}" y1="{y:.2f}" '
                f'x2="{left + plot_width}" y2="{y:.2f}" '
                'stroke="#dddddd"/>'
            )
            elements.append(
                f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" '
                'font-family="sans-serif" font-size="11">'
                f"{value:.1f}</text>"
            )

        for tick in range(6):
            load_factor = tick / 5
            x = x_position(load_factor)
            elements.append(
                f'<line x1="{x:.2f}" y1="{plot_top}" '
                f'x2="{x:.2f}" y2="{plot_bottom}" stroke="#eeeeee"/>'
            )
            elements.append(
                f'<text x="{x:.2f}" y="{plot_bottom + 20}" '
                'text-anchor="middle" font-family="sans-serif" font-size="11">'
                f"{load_factor:.1f}</text>"
            )

        elements.extend(
            (
                f'<line x1="{left}" y1="{plot_top}" x2="{left}" '
                f'y2="{plot_bottom}" stroke="#333333"/>',
                f'<line x1="{left}" y1="{plot_bottom}" '
                f'x2="{left + plot_width}" y2="{plot_bottom}" '
                'stroke="#333333"/>',
                (
                    f'<text x="{left + plot_width / 2}" y="{plot_bottom + 45}" '
                    'text-anchor="middle" font-family="sans-serif" font-size="13">'
                    "Load factor (items / 4093)</text>"
                ),
                (
                    f'<text x="{left - 55}" y="{plot_top + plot_height / 2}" '
                    f'transform="rotate(-90 {left - 55} '
                    f'{plot_top + plot_height / 2})" text-anchor="middle" '
                    'font-family="sans-serif" font-size="13">'
                    "Average comparisons</text>"
                ),
            )
        )

        for table_name, _, color in table_series:
            for attribute, dash_array in (
                (measured_attribute, ""),
                (theoretical_attribute, "7 5"),
            ):
                points = " ".join(
                    f"{x_position(result.actual_load_factor):.2f},"
                    f"{y_position(getattr(getattr(result, table_name), attribute)):.2f}"
                    for result in results
                )
                dash = (
                    f' stroke-dasharray="{dash_array}"' if dash_array else ""
                )
                elements.append(
                    f'<polyline points="{points}" fill="none" '
                    f'stroke="{color}" stroke-width="2"{dash}/>'
                )
                for result in results:
                    value = getattr(getattr(result, table_name), attribute)
                    elements.append(
                        f'<circle cx="{x_position(result.actual_load_factor):.2f}" '
                        f'cy="{y_position(value):.2f}" r="2.5" fill="{color}"/>'
                    )

    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def print_table(results: list[ExperimentResult]) -> None:
    print(
        "target alpha | actual alpha | items | table | success measured | "
        "success theory | failure measured | failure theory"
    )
    for result in results:
        for table_name in ("chaining", "linear"):
            table_result = getattr(result, table_name)
            print(
                f"{result.target_load_factor:12.1f} | "
                f"{result.actual_load_factor:12.4f} | "
                f"{result.item_count:5d} | {table_name:7s} | "
                f"{table_result.measured_success_average:16.4f} | "
                f"{table_result.theoretical_success_average:14.4f} | "
                f"{table_result.measured_failure_average:16.4f} | "
                f"{table_result.theoretical_failure_average:14.4f}"
            )


def main() -> None:
    results = run_experiment()
    write_csv(results)
    SVG_PATH.write_text(make_svg(results), encoding="utf-8")
    print_table(results)
    print(f"\nWrote {CSV_PATH}")
    print(f"Wrote {SVG_PATH}")


if __name__ == "__main__":
    main()
