"""CSV recording and replay helpers for reproducible simulator runs."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass


@dataclass(frozen=True)
class ReplaySample:
    time_s: float
    channels: list[int]


def samples_to_csv(samples: list[ReplaySample]) -> str:
    output = io.StringIO()
    fieldnames = ["time_s", *[f"ch{index + 1}" for index in range(16)]]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for sample in samples:
        row = {"time_s": f"{sample.time_s:.6f}"}
        row.update({f"ch{index + 1}": value for index, value in enumerate((sample.channels + [1500] * 16)[:16])})
        writer.writerow(row)
    return output.getvalue()


def parse_csv(text: str) -> list[ReplaySample]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "time_s" not in reader.fieldnames:
        raise ValueError("CSV must contain a time_s column")
    required = [f"ch{index + 1}" for index in range(16)]
    missing = [name for name in required if name not in reader.fieldnames]
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(missing)}")
    result: list[ReplaySample] = []
    for row in reader:
        result.append(ReplaySample(float(row["time_s"]), [int(float(row[name])) for name in required]))
    return sorted(result, key=lambda item: item.time_s)
