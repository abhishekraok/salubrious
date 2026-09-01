#!/usr/bin/env python3
"""Normalize the read-only Google Sheets ``Assets`` reference into .private.

The script accepts a connector payload on stdin. The sheet is explicitly a
secondary, potentially inconsistent source: it can corroborate context and
surface missing activity, but it never overwrites statement-derived rows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / ".private" / "finance"
SHEET_DATE_FORMATS = ("%m/%d/%Y", "%m/%d/%y", "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d")
KNOWN_NON_TICKERS = {
    "TOTAL",
    "CASH",
    "TARGET",
    "DEVELOPED",
    "EMERGING",
    "VANGUARD",
    "NON TAXABLE",
    "TAXABLE",
    "STOCKS",
    "REITS",
}

SNAPSHOT_FIELDS = [
    "schema_version",
    "snapshot_id",
    "source",
    "sheet_tab",
    "source_row",
    "snapshot_date",
    "year_context",
    "symbol",
    "security_name",
    "market_value_raw",
    "value_unit",
    "market_value_usd",
    "evidence_role",
    "parse_confidence",
]

ACTION_NOTE_FIELDS = [
    "schema_version",
    "note_id",
    "source",
    "sheet_tab",
    "source_cell",
    "year_context",
    "inferred_date",
    "note_type",
    "tickers",
    "note",
    "evidence_role",
    "parse_confidence",
]

TIMELINE_FIELDS = [
    "schema_version",
    "source",
    "sheet_tab",
    "source_row",
    "year",
    "income_after_tax",
    "tax",
    "savings",
    "expenses",
    "assets",
    "appreciation",
    "interest",
    "evidence_role",
]


def require_private_output(path: Path) -> Path:
    """Resolve an output path and reject locations that could be tracked by git."""

    private_root = (REPO_ROOT / ".private").resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise ValueError("output-dir must be inside the repository's .private directory") from exc
    return resolved


def stable_id(*parts: object) -> str:
    joined = "\x1f".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\u00a0", " ")).strip()


def parse_number(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = clean_text(value)
    if not text or text in {"-", "—"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.replace("$", "").replace(",", "").replace("%", "")
    text = text.replace("+", "").replace("(", "").replace(")", "")
    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return None
    return -parsed if negative else parsed


def decimal_text(value: Decimal | None) -> str:
    return "" if value is None else format(value, "f")


def parse_date_text(value: object, *, year_context: int | None = None) -> date | None:
    text = clean_text(value)
    for fmt in SHEET_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    if year_context:
        explicit = re.search(
            r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
            r"\s+(\d{1,2})\b",
            text,
            re.I,
        )
        if explicit:
            try:
                return datetime.strptime(
                    f"{explicit.group(1)[:3]} {explicit.group(2)} {year_context}", "%b %d %Y"
                ).date()
            except ValueError:
                return None
    return None


def cell(row: list[Any], index: int) -> Any:
    return row[index] if index < len(row) else ""


def column_letter(index: int) -> str:
    value = index + 1
    output = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        output = chr(65 + remainder) + output
    return output


def detect_value_unit(header: str, tab: str) -> tuple[str, Decimal | None]:
    normalized = header.lower()
    if "k$" in normalized or "(k)" in normalized or "(k$)" in normalized:
        return "USD thousands", Decimal("1000")
    if tab in {"2024", "2025", "2026"} and normalized in {"value", "amount"}:
        return "USD thousands (sheet convention)", Decimal("1000")
    if any(token in normalized for token in ("value", "amount", "current")):
        return "USD", Decimal("1")
    return "unknown", None


def normalize_symbol(value: object) -> tuple[str, str]:
    name = clean_text(value)
    candidate = name.upper().strip()
    if re.fullmatch(r"[A-Z]{1,5}", candidate) and candidate not in KNOWN_NON_TICKERS:
        return candidate, name
    ticker_match = re.match(r"^([A-Z]{1,5})\b", candidate)
    if ticker_match and ticker_match.group(1) not in KNOWN_NON_TICKERS:
        return ticker_match.group(1), name
    return "", name


def extract_snapshots(tab: str, formatted: list[list[Any]], values: list[list[Any]]) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    try:
        year_context = int(tab)
    except ValueError:
        return snapshots

    for row_index, formatted_row in enumerate(formatted):
        first = clean_text(cell(formatted_row, 0)).lower()
        second = clean_text(cell(formatted_row, 1))
        if first not in {"symbol", "stocks"}:
            continue
        if not any(token in second.lower() for token in ("value", "amount", "market value", "current")):
            continue

        snapshot_date = None
        for previous in range(row_index - 1, max(-1, row_index - 5), -1):
            candidate = parse_date_text(cell(formatted[previous], 0), year_context=year_context)
            if candidate:
                snapshot_date = candidate
                break
        value_unit, multiplier = detect_value_unit(second, tab)

        data_index = row_index + 1
        while data_index < len(formatted):
            name_value = clean_text(cell(formatted[data_index], 0))
            if not name_value:
                break
            if name_value.lower().startswith("total"):
                break
            raw_value = cell(values[data_index], 1) if data_index < len(values) else ""
            numeric = parse_number(raw_value)
            if numeric is None:
                data_index += 1
                continue
            symbol, security_name = normalize_symbol(name_value)
            usd_value = numeric * multiplier if multiplier is not None else None
            snapshot_id = stable_id("assets-sheet-snapshot", tab, data_index + 1, snapshot_date, name_value)
            snapshots.append(
                {
                    "schema_version": "1",
                    "snapshot_id": snapshot_id,
                    "source": "google_sheet_assets",
                    "sheet_tab": tab,
                    "source_row": data_index + 1,
                    "snapshot_date": snapshot_date.isoformat() if snapshot_date else "",
                    "year_context": year_context,
                    "symbol": symbol,
                    "security_name": security_name,
                    "market_value_raw": decimal_text(numeric),
                    "value_unit": value_unit,
                    "market_value_usd": decimal_text(usd_value),
                    "evidence_role": "secondary_unverified",
                    "parse_confidence": "medium" if snapshot_date and multiplier else "low",
                }
            )
            data_index += 1
    return snapshots


def extract_action_notes(tab: str, formatted: list[list[Any]]) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    try:
        year_context = int(tab)
    except ValueError:
        year_context = None

    pattern = re.compile(r"\b(?:buy|bought|sell|sold|rebalance)\b", re.I)
    for row_index, row in enumerate(formatted):
        for column_index, value in enumerate(row):
            note = clean_text(value)
            if not pattern.search(note):
                continue
            past_tense = bool(re.search(r"\b(?:bought|sold)\b", note, re.I))
            note_type = "reported_completed" if past_tense else "planned_or_ambiguous"
            inferred = parse_date_text(note, year_context=year_context)
            tickers = sorted(
                {
                    token
                    for token in re.findall(r"\b[A-Z]{2,5}\b", note.upper())
                    if token not in {"BUY", "BOUGHT", "SELL", "SOLD", "DONE", "JAN", "SEP", "NOV"}
                }
            )
            address = f"{column_letter(column_index)}{row_index + 1}"
            notes.append(
                {
                    "schema_version": "1",
                    "note_id": stable_id("assets-sheet-note", tab, address, note),
                    "source": "google_sheet_assets",
                    "sheet_tab": tab,
                    "source_cell": address,
                    "year_context": year_context or "",
                    "inferred_date": inferred.isoformat() if inferred else "",
                    "note_type": note_type,
                    "tickers": ";".join(tickers),
                    "note": note,
                    "evidence_role": "secondary_unverified",
                    "parse_confidence": "medium" if past_tense and inferred else "low",
                }
            )
    return notes


def extract_timeline(formatted: list[list[Any]], values: list[list[Any]]) -> list[dict[str, Any]]:
    if not formatted:
        return []
    headers = [clean_text(value).lower() for value in formatted[0]]
    expected = {
        "year": "year",
        "income (after tax)": "income_after_tax",
        "tax": "tax",
        "savings": "savings",
        "expenses": "expenses",
        "assets": "assets",
        "appreciation": "appreciation",
        "interest": "interest",
    }
    indexes = {output: headers.index(header) for header, output in expected.items() if header in headers}
    if "year" not in indexes:
        return []
    result: list[dict[str, Any]] = []
    for row_index in range(1, min(len(formatted), len(values))):
        year_number = parse_number(cell(values[row_index], indexes["year"]))
        if year_number is None or year_number < 1900 or year_number > 2200:
            continue
        row: dict[str, Any] = {
            "schema_version": "1",
            "source": "google_sheet_assets",
            "sheet_tab": "Timeline",
            "source_row": row_index + 1,
            "year": int(year_number),
            "evidence_role": "secondary_unverified",
        }
        for field in TIMELINE_FIELDS:
            if field in indexes:
                row[field] = decimal_text(parse_number(cell(values[row_index], indexes[field])))
        result.append(row)
    return result


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def import_payload(payload: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    tabs = payload.get("tabs", [])
    snapshots: list[dict[str, Any]] = []
    action_notes: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    for tab in tabs:
        title = clean_text(tab.get("title"))
        formatted = tab.get("formatted_values") or []
        values = tab.get("unformatted_values") or []
        snapshots.extend(extract_snapshots(title, formatted, values))
        action_notes.extend(extract_action_notes(title, formatted))
        if title == "Timeline":
            timeline.extend(extract_timeline(formatted, values))

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        output_dir.chmod(0o700)
        output_dir.parent.chmod(0o700)
    except OSError:
        pass
    write_csv(output_dir / "assets_sheet_snapshots.csv", snapshots, SNAPSHOT_FIELDS)
    write_csv(output_dir / "assets_sheet_action_notes.csv", action_notes, ACTION_NOTE_FIELDS)
    write_csv(output_dir / "assets_sheet_timeline.csv", timeline, TIMELINE_FIELDS)

    content_hash = hashlib.sha256(
        json.dumps(tabs, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    metadata = {
        "schema_version": 1,
        "source": "google_sheet_assets",
        "spreadsheet_id": payload.get("spreadsheet_id"),
        "spreadsheet_title": payload.get("title", "Assets"),
        "spreadsheet_url": payload.get("url"),
        "source_modified_time": payload.get("modified_time"),
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "content_sha256": content_hash,
        "evidence_role": "secondary_unverified",
        "precedence": "PDF ledgers and statements remain authoritative on conflicts.",
        "raw_grid_persisted": False,
        "counts": {
            "tabs_read": len(tabs),
            "snapshot_rows": len(snapshots),
            "action_notes": len(action_notes),
            "timeline_rows": len(timeline),
        },
    }
    (output_dir / "assets_sheet_source.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    output_dir = require_private_output(args.output_dir)
    payload_chunks: list[str] = []
    for line in sys.stdin:
        if line.rstrip("\r\n") == "__END__":
            break
        payload_chunks.append(line.rstrip("\r\n"))
    payload = json.loads("".join(payload_chunks))
    metadata = import_payload(payload, output_dir)
    counts = metadata["counts"]
    print(
        f"Imported Assets reference: {counts['snapshot_rows']} snapshot rows, "
        f"{counts['action_notes']} action notes, {counts['timeline_rows']} timeline rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
