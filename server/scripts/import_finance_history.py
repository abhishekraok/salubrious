#!/usr/bin/env python3
"""Normalize local statement PDFs and build private decision-quality inputs.

The raw PDFs are read in place and never copied into the repository. All derived
files are written below ``.private/finance`` by default, which is gitignored.
No names, addresses, employer names, or account numbers are persisted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = REPO_ROOT / "server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
DEFAULT_OUTPUT_DIR = REPO_ROOT / ".private" / "finance"
PARSER_VERSION = "1.0.0"
DATE_TOKEN = r"\d{1,2}/\d{1,2}/\d{4}"
MONEY_TOKEN_RE = re.compile(r"(?:\$?\(?[+-]?[0-9][0-9,]*(?:\.[0-9]+)?\)?|—|-)")

TRANSACTION_FIELDS = [
    "schema_version",
    "event_id",
    "source_id",
    "source_file",
    "source_page",
    "source_row",
    "institution",
    "account_key",
    "account_type_or_source_bucket",
    "trade_date",
    "settlement_date",
    "effective_date",
    "action_raw",
    "action",
    "decision_kind",
    "symbol",
    "security_name",
    "quantity_raw",
    "quantity",
    "price_raw",
    "unit_price",
    "fees_raw",
    "fees",
    "amount_raw",
    "amount",
    "currency",
    "units_delta",
    "cash_effect",
    "external_flow",
    "parse_confidence",
    "raw_row_hash",
]

PERFORMANCE_FIELDS = [
    "schema_version",
    "period_id",
    "source_id",
    "source_file",
    "institution",
    "account_key",
    "period_start",
    "period_end",
    "beginning_value",
    "external_contributions",
    "withdrawals",
    "transfers_in",
    "transfers_out",
    "fees",
    "income",
    "investment_gain_loss",
    "ending_value",
    "personal_return_pct",
    "annualized_return_pct",
    "currency",
    "parse_confidence",
]

WARNING_FIELDS = ["source_id", "source_file", "page", "row", "code", "field", "severity"]


@dataclass
class ParsedSource:
    source: dict[str, Any]
    transactions: list[dict[str, Any]]
    periods: list[dict[str, Any]]
    warnings: list[dict[str, Any]]


def require_private_output(path: Path) -> Path:
    """Resolve an output path and reject locations that could be tracked by git."""

    private_root = (REPO_ROOT / ".private").resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise ValueError("output-dir must be inside the repository's .private directory") from exc
    return resolved


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_id(*parts: object, length: int = 24) -> str:
    value = "\x1f".join("" if part is None else str(part) for part in parts)
    return sha256_bytes(value.encode("utf-8"))[:length]


def clean_text(value: str) -> str:
    value = value.replace("…", "...").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def parse_us_date(value: str) -> date | None:
    value = clean_text(value)
    for fmt in ("%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def iso(value: date | None) -> str:
    return value.isoformat() if value else ""


def parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    normalized = clean_text(value)
    if normalized in {"", "-", "—", "--", "not applicable"}:
        return None
    if normalized.lower() == "free":
        return Decimal("0")
    negative_parentheses = normalized.startswith("(") and normalized.endswith(")")
    normalized = normalized.replace("$", "").replace(",", "").replace("%", "")
    normalized = normalized.replace("+", "").replace("(", "").replace(")", "")
    try:
        number = Decimal(normalized)
    except InvalidOperation:
        return None
    return -number if negative_parentheses else number


def decimal_text(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value, "f")


def run_pdftotext(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def warning(
    source_id: str,
    source_file: str,
    code: str,
    *,
    page: int | str = "",
    row: int | str = "",
    field: str = "",
    severity: str = "warning",
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_file": source_file,
        "page": page,
        "row": row,
        "code": code,
        "field": field,
        "severity": severity,
    }


ROTH_ACTIONS: list[tuple[re.Pattern[str], tuple[str, str]]] = [
    (re.compile(r"Reinvestment\s*\(LT\s*gain\)", re.I), ("reinvest", "automatic")),
    (re.compile(r"Capital\s+gain\s*\(LT\)", re.I), ("capital_gain", "automatic")),
    (re.compile(r"Conversion\s*\(incoming\)", re.I), ("conversion", "external_flow")),
    (re.compile(r"Sell\s*\(exchange\)", re.I), ("exchange_sell", "reallocation")),
    (re.compile(r"Buy\s*\(exchange\)", re.I), ("exchange_buy", "reallocation")),
    (re.compile(r"Reinvestment", re.I), ("reinvest", "automatic")),
    (re.compile(r"Dividend", re.I), ("dividend", "automatic")),
    (re.compile(r"Sweep\s+out", re.I), ("sweep_out", "cash_management")),
    (re.compile(r"Sweep\s+in", re.I), ("sweep_in", "cash_management")),
    (re.compile(r"Sell", re.I), ("sell", "trade")),
    (re.compile(r"Buy", re.I), ("buy", "trade")),
]


VANGUARD_PLAN_ACTIONS: list[tuple[re.Pattern[str], tuple[str, str]]] = [
    (re.compile(r"Fund\s+to\s+Fund\s+Out", re.I), ("exchange_sell", "reallocation")),
    (re.compile(r"Fund\s+to\s+Fund\s+In", re.I), ("exchange_buy", "reallocation")),
    (re.compile(r"Plan\s+Contribution", re.I), ("contribution", "contribution")),
]


def find_action(
    value: str, patterns: list[tuple[re.Pattern[str], tuple[str, str]]]
) -> tuple[re.Match[str] | None, str, str]:
    for pattern, (action, decision_kind) in patterns:
        match = pattern.search(value)
        if match:
            return match, action, decision_kind
    return None, "unknown", "unknown"


def numeric_tokens(value: str) -> list[str]:
    return [match.group(0) for match in MONEY_TOKEN_RE.finditer(value)]


def canonical_transaction(
    *,
    source_id: str,
    source_file: str,
    source_page: int,
    source_row: int,
    institution: str,
    account_key: str,
    account_bucket: str,
    trade_date: date | None,
    settlement_date: date | None,
    action_raw: str,
    action: str,
    decision_kind: str,
    symbol: str,
    security_name: str,
    quantity_raw: str,
    price_raw: str,
    fees_raw: str,
    amount_raw: str,
    confidence: str,
) -> dict[str, Any]:
    quantity = parse_decimal(quantity_raw)
    unit_price = parse_decimal(price_raw)
    fees = parse_decimal(fees_raw)
    amount = parse_decimal(amount_raw)
    effective = trade_date or settlement_date

    units_delta: Decimal | None = None
    if quantity is not None:
        if action in {"buy", "exchange_buy", "reinvest", "contribution", "conversion"}:
            units_delta = abs(quantity)
        elif action in {"sell", "exchange_sell"}:
            units_delta = -abs(quantity)

    external_flow: Decimal | None = None
    if action in {"contribution", "conversion"} and amount is not None:
        external_flow = abs(amount)

    cash_effect: Decimal | None = None
    if amount is not None:
        if action in {"buy", "reinvest", "sweep_in"}:
            cash_effect = -abs(amount)
        elif action in {"sell", "dividend", "capital_gain", "sweep_out"}:
            cash_effect = abs(amount)

    raw_fingerprint = "|".join(
        [
            source_id,
            str(source_page),
            str(source_row),
            iso(trade_date),
            iso(settlement_date),
            action_raw,
            symbol,
            quantity_raw,
            price_raw,
            fees_raw,
            amount_raw,
        ]
    )
    raw_row_hash = sha256_bytes(raw_fingerprint.encode("utf-8"))
    event_id = stable_id("transaction", raw_row_hash)
    return {
        "schema_version": "1",
        "event_id": event_id,
        "source_id": source_id,
        "source_file": source_file,
        "source_page": source_page,
        "source_row": source_row,
        "institution": institution,
        "account_key": account_key,
        "account_type_or_source_bucket": clean_text(account_bucket),
        "trade_date": iso(trade_date),
        "settlement_date": iso(settlement_date),
        "effective_date": iso(effective),
        "action_raw": clean_text(action_raw),
        "action": action,
        "decision_kind": decision_kind,
        "symbol": "" if symbol in {"—", "-"} else clean_text(symbol).upper(),
        "security_name": clean_text(security_name),
        "quantity_raw": clean_text(quantity_raw),
        "quantity": decimal_text(quantity),
        "price_raw": clean_text(price_raw),
        "unit_price": decimal_text(unit_price),
        "fees_raw": clean_text(fees_raw),
        "fees": decimal_text(fees),
        "amount_raw": clean_text(amount_raw),
        "amount": decimal_text(amount),
        "currency": "USD",
        "units_delta": decimal_text(units_delta),
        "cash_effect": decimal_text(cash_effect),
        "external_flow": decimal_text(external_flow),
        "parse_confidence": confidence,
        "raw_row_hash": raw_row_hash,
    }


def parse_roth_ledger(text: str, source_id: str, source_file: str) -> ParsedSource:
    transactions: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    row_number = 0

    for page_number, page in enumerate(text.split("\f"), start=1):
        lines = page.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            if not re.match(rf"^\s*{DATE_TOKEN}\s+{DATE_TOKEN}\b", line):
                index += 1
                continue

            block = [line]
            lookahead = index + 1
            while lookahead < len(lines):
                following = lines[lookahead]
                if not following.strip() or re.match(rf"^\s*{DATE_TOKEN}\b", following):
                    break
                if following.lstrip().startswith(("Page ", "Settlement", "Custom report")):
                    break
                block.append(following)
                lookahead += 1

            row_number += 1
            date_match = re.match(
                rf"^\s*(?P<settlement>{DATE_TOKEN})\s+(?P<trade>{DATE_TOKEN})\s+(?P<symbol>\S+)",
                line,
            )
            if not date_match:
                warnings.append(
                    warning(source_id, source_file, "unparsed_dates", page=page_number, row=row_number, field="date")
                )
                index = max(index + 1, lookahead)
                continue

            action_context = " ".join(
                part for part in [line[87:106].strip(), *(item[87:106].strip() for item in block[1:])] if part
            )
            action_match, action, decision_kind = find_action(action_context, ROTH_ACTIONS)
            if action_match is None:
                warnings.append(
                    warning(source_id, source_file, "unknown_action", page=page_number, row=row_number, field="action")
                )
                index = max(index + 1, lookahead)
                continue

            symbol = date_match.group("symbol")
            name = line[40:87].strip()
            for continuation in block[1:]:
                continuation_name = continuation[40:87].strip()
                if continuation_name:
                    name = f"{name} {continuation_name}".strip()

            quantity_raw = line[116:131].strip()
            price_raw = line[131:143].strip()
            fees_raw = line[143:162].strip()
            amount_raw = line[162:].strip()

            account_bucket = line[106:116].strip()
            trade_date = parse_us_date(date_match.group("trade"))
            settlement_date = parse_us_date(date_match.group("settlement"))
            confidence = "high" if trade_date and settlement_date and action != "unknown" else "low"
            transactions.append(
                canonical_transaction(
                    source_id=source_id,
                    source_file=source_file,
                    source_page=page_number,
                    source_row=row_number,
                    institution="Vanguard",
                    account_key="vanguard-roth-ira",
                    account_bucket=account_bucket or "Roth IRA brokerage",
                    trade_date=trade_date,
                    settlement_date=settlement_date,
                    action_raw=action_match.group(0),
                    action=action,
                    decision_kind=decision_kind,
                    symbol=symbol,
                    security_name=name,
                    quantity_raw=quantity_raw,
                    price_raw=price_raw,
                    fees_raw=fees_raw,
                    amount_raw=amount_raw,
                    confidence=confidence,
                )
            )
            index = max(index + 1, lookahead)

    source = source_record(
        source_id=source_id,
        source_file=source_file,
        source_kind="ledger",
        institution="Vanguard",
        account_key="vanguard-roth-ira",
        text=text,
        transactions=transactions,
        periods=[],
        warnings=warnings,
    )
    return ParsedSource(source, transactions, [], warnings)


def parse_vanguard_plan_ledger(text: str, source_id: str, source_file: str) -> ParsedSource:
    transactions: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    row_number = 0

    for page_number, page in enumerate(text.split("\f"), start=1):
        lines = page.splitlines()
        for line_index, line in enumerate(lines):
            if not re.match(rf"^{DATE_TOKEN}\b", line):
                continue
            row_number += 1
            date_match = re.match(rf"^(?P<trade>{DATE_TOKEN})", line)
            symbol_match = re.match(rf"^{DATE_TOKEN}\s+(?P<symbol>\S+)", line)
            action_match, action, decision_kind = find_action(line, VANGUARD_PLAN_ACTIONS)
            if date_match is None or symbol_match is None or action_match is None:
                warnings.append(
                    warning(source_id, source_file, "unknown_action", page=page_number, row=row_number, field="action")
                )
                continue

            # Later exported pages are shifted two characters left. Anchor the
            # name and symbol columns to the observed Type-column position.
            column_offset = action_match.start() - 81
            name_start = max(0, 38 + column_offset)
            account_start = max(0, 61 + column_offset)
            symbol = symbol_match.group("symbol")
            name = line[name_start:account_start].strip()

            continuation_index = line_index + 1
            while continuation_index < len(lines):
                continuation = lines[continuation_index]
                if not continuation.strip() or re.match(rf"^{DATE_TOKEN}\b", continuation):
                    break
                if continuation.lstrip().startswith(("Date ", "Showing rows", "More account", "Transaction")):
                    break
                continuation_name = continuation[name_start:account_start].strip()
                if continuation_name and continuation_name not in name:
                    name = f"{name} {continuation_name}".strip()
                continuation_index += 1

            tokens = numeric_tokens(line[action_match.end() :])
            if len(tokens) < 4:
                warnings.append(
                    warning(source_id, source_file, "missing_numeric_columns", page=page_number, row=row_number)
                )
                tokens = (["—"] * (4 - len(tokens))) + tokens
            quantity_raw, price_raw, fees_raw, amount_raw = tokens[-4:]
            trade_date = parse_us_date(date_match.group("trade"))
            confidence = "high" if trade_date and action != "unknown" else "low"
            transactions.append(
                canonical_transaction(
                    source_id=source_id,
                    source_file=source_file,
                    source_page=page_number,
                    source_row=row_number,
                    institution="Vanguard",
                    account_key="vanguard-employer-401k",
                    account_bucket="employer retirement plan",
                    trade_date=trade_date,
                    settlement_date=None,
                    action_raw=action_match.group(0),
                    action=action,
                    decision_kind=decision_kind,
                    symbol=symbol,
                    security_name=name,
                    quantity_raw=quantity_raw,
                    price_raw=price_raw,
                    fees_raw=fees_raw,
                    amount_raw=amount_raw,
                    confidence=confidence,
                )
            )

    source = source_record(
        source_id=source_id,
        source_file=source_file,
        source_kind="ledger",
        institution="Vanguard",
        account_key="vanguard-employer-401k",
        text=text,
        transactions=transactions,
        periods=[],
        warnings=warnings,
    )
    return ParsedSource(source, transactions, [], warnings)


def line_amount(block: str, label: str) -> Decimal | None:
    pattern = re.compile(rf"^\s*{re.escape(label)}\s+([+$()0-9,.-]+|—)\s*$", re.M)
    match = pattern.search(block)
    return parse_decimal(match.group(1)) if match else None


def make_period(
    *,
    source_id: str,
    source_file: str,
    institution: str,
    account_key: str,
    period_start: date | None,
    period_end: date | None,
    beginning_value: Decimal | None,
    contributions: Decimal | None,
    withdrawals: Decimal | None,
    transfers_in: Decimal | None,
    transfers_out: Decimal | None,
    fees: Decimal | None,
    income: Decimal | None,
    investment_gain_loss: Decimal | None,
    ending_value: Decimal | None,
    personal_return: Decimal | None,
    annualized_return: Decimal | None,
    confidence: str,
) -> dict[str, Any]:
    period_id = stable_id("period", source_id, account_key, iso(period_start), iso(period_end))
    return {
        "schema_version": "1",
        "period_id": period_id,
        "source_id": source_id,
        "source_file": source_file,
        "institution": institution,
        "account_key": account_key,
        "period_start": iso(period_start),
        "period_end": iso(period_end),
        "beginning_value": decimal_text(beginning_value),
        "external_contributions": decimal_text(contributions),
        "withdrawals": decimal_text(withdrawals),
        "transfers_in": decimal_text(transfers_in),
        "transfers_out": decimal_text(transfers_out),
        "fees": decimal_text(fees),
        "income": decimal_text(income),
        "investment_gain_loss": decimal_text(investment_gain_loss),
        "ending_value": decimal_text(ending_value),
        "personal_return_pct": decimal_text(personal_return),
        "annualized_return_pct": decimal_text(annualized_return),
        "currency": "USD",
        "parse_confidence": confidence,
    }


def parse_fidelity_statement(text: str, source_id: str, source_file: str) -> ParsedSource:
    warnings: list[dict[str, Any]] = []
    periods: list[dict[str, Any]] = []
    start_re = re.compile(
        r"^\s*Beginning Account Value as of (?P<date>[A-Z][a-z]{2} \d{1,2},\s*\d{4})\s+(?P<value>\$?[0-9,.-]+|—|-)",
        re.M,
    )
    end_re = re.compile(
        r"^\s*Ending Account Value as of (?P<date>[A-Z][a-z]{2} \d{1,2},\s*\d{4})(?:\s*\*+)?\s+(?P<value>\$?[0-9,.-]+|—|-)",
        re.M,
    )
    starts = list(start_re.finditer(text))
    for period_index, start_match in enumerate(starts, start=1):
        end_match = end_re.search(text, start_match.end())
        if end_match is None:
            warnings.append(warning(source_id, source_file, "missing_period_end", row=period_index, field="period_end"))
            continue
        block = text[start_match.start() : end_match.end()]
        period_start = parse_us_date(re.sub(r",\s*", ", ", start_match.group("date")))
        period_end = parse_us_date(re.sub(r",\s*", ", ", end_match.group("date")))
        beginning = parse_decimal(start_match.group("value")) or Decimal("0")
        ending = parse_decimal(end_match.group("value"))
        page_start = text.rfind("\f", 0, start_match.start()) + 1
        page_end = text.find("\f", start_match.start())
        page_text = text[page_start : page_end if page_end >= 0 else len(text)]
        if "EMPLOYEE STOCK PURCHASE" in page_text.upper():
            account_key = "fidelity-espp"
        else:
            account_key = "fidelity-taxable-brokerage"
        return_match = re.search(r"Total Account Return[^:]*:\s*([+-]?[0-9.]+)%", text[end_match.end() : end_match.end() + 1600])
        personal_return = parse_decimal(return_match.group(1)) if return_match else None
        confidence = "high" if period_start and period_end and ending is not None else "medium"
        periods.append(
            make_period(
                source_id=source_id,
                source_file=source_file,
                institution="Fidelity",
                account_key=account_key,
                period_start=period_start,
                period_end=period_end,
                beginning_value=beginning,
                contributions=line_amount(block, "Deposits"),
                withdrawals=line_amount(block, "Withdrawals"),
                transfers_in=line_amount(block, "Securities Transferred In"),
                transfers_out=line_amount(block, "Securities Transferred Out"),
                fees=line_amount(block, "Transaction Costs, Fees & Charges"),
                income=None,
                investment_gain_loss=line_amount(block, "Change in Investment Value *"),
                ending_value=ending,
                personal_return=personal_return,
                annualized_return=None,
                confidence=confidence,
            )
        )

    # Some Fidelity PDFs repeat the same account summary in a compact overview
    # and again in the detailed section. Keep the more complete copy so those
    # repeated panels do not become duplicate performance periods.
    deduplicated: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    completeness_fields = (
        "external_contributions",
        "withdrawals",
        "transfers_in",
        "transfers_out",
        "fees",
        "income",
        "investment_gain_loss",
        "personal_return_pct",
    )
    for period in periods:
        key = (
            period["account_key"],
            period["period_start"],
            period["period_end"],
            period["ending_value"],
        )
        current = deduplicated.get(key)
        score = sum(bool(period[field]) for field in completeness_fields)
        current_score = sum(bool(current[field]) for field in completeness_fields) if current else -1
        if score >= current_score:
            deduplicated[key] = period
    periods = list(deduplicated.values())

    if not periods:
        warnings.append(warning(source_id, source_file, "no_performance_period", severity="error"))
    source = source_record(
        source_id=source_id,
        source_file=source_file,
        source_kind="statement",
        institution="Fidelity",
        account_key="multiple-fidelity-accounts" if len(periods) > 1 else "fidelity-taxable-brokerage",
        text=text,
        transactions=[],
        periods=periods,
        warnings=warnings,
    )
    return ParsedSource(source, [], periods, warnings)


def parse_schwab_performance(text: str, source_id: str, source_file: str) -> ParsedSource:
    warnings: list[dict[str, Any]] = []
    periods: list[dict[str, Any]] = []
    return_match = re.search(
        r"cumulative rate of return of\s+([+-]?[0-9.]+)%\s+from\s+([A-Z][a-z]+ \d{1,2}, \d{4})\s+to\s+([A-Z][a-z]+ \d{1,2}, \d{4})(?:\.\s*\(Annualized:\s*([+-]?[0-9.]+)%\))?",
        text,
        re.I,
    )
    if return_match:
        period_start = parse_us_date(return_match.group(2))
        period_end = parse_us_date(return_match.group(3))
        personal_return = parse_decimal(return_match.group(1))
        annualized_return = parse_decimal(return_match.group(4)) if return_match.group(4) else None
    else:
        period_start = period_end = None
        personal_return = annualized_return = None
        warnings.append(warning(source_id, source_file, "missing_reported_return", field="personal_return_pct"))

    first_section_end = text.find("What do these terms mean?")
    block = text[: first_section_end if first_section_end > 0 else len(text)]
    beginning = line_amount(block, "Beginning Value")
    ending = line_amount(block, "Ending Value")
    confidence = "high" if period_start and period_end and beginning is not None and ending is not None else "medium"
    periods.append(
        make_period(
            source_id=source_id,
            source_file=source_file,
            institution="Charles Schwab",
            account_key="schwab-taxable-portfolio",
            period_start=period_start,
            period_end=period_end,
            beginning_value=beginning,
            contributions=line_amount(block, "Contributions"),
            withdrawals=line_amount(block, "Withdrawals"),
            transfers_in=None,
            transfers_out=None,
            fees=line_amount(block, "Fees & Expenses"),
            income=line_amount(block, "Income"),
            investment_gain_loss=line_amount(block, "Investment Gain/Loss"),
            ending_value=ending,
            personal_return=personal_return,
            annualized_return=annualized_return,
            confidence=confidence,
        )
    )
    source = source_record(
        source_id=source_id,
        source_file=source_file,
        source_kind="performance",
        institution="Charles Schwab",
        account_key="schwab-taxable-portfolio",
        text=text,
        transactions=[],
        periods=periods,
        warnings=warnings,
    )
    return ParsedSource(source, [], periods, warnings)


def source_record(
    *,
    source_id: str,
    source_file: str,
    source_kind: str,
    institution: str,
    account_key: str,
    text: str,
    transactions: list[dict[str, Any]],
    periods: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    dates = [
        row.get("effective_date") or row.get("period_start")
        for row in [*transactions, *periods]
        if row.get("effective_date") or row.get("period_start")
    ]
    end_dates = [
        row.get("effective_date") or row.get("period_end")
        for row in [*transactions, *periods]
        if row.get("effective_date") or row.get("period_end")
    ]
    return {
        "source_id": source_id,
        "source_kind": source_kind,
        "institution": institution,
        "account_key": account_key,
        "source_file": source_file,
        "parser_version": PARSER_VERSION,
        "period_start": min(dates) if dates else "",
        "period_end": max(end_dates) if end_dates else "",
        "page_count": len([page for page in text.split("\f") if page.strip()]),
        "parsed_row_count": len(transactions) + len(periods),
        "warning_count": len(warnings),
    }


def parse_source(path: Path) -> ParsedSource:
    source_hash = sha256_bytes(path.read_bytes())
    source_id = stable_id("source", source_hash)
    text = run_pdftotext(path)
    source_file = path.name
    if "Roth IRA transactions" in source_file:
        parsed = parse_roth_ledger(text, source_id, source_file)
    elif "Vanguard 401K transactions" in source_file:
        parsed = parse_vanguard_plan_ledger(text, source_id, source_file)
    elif source_file.startswith("Fidelity "):
        parsed = parse_fidelity_statement(text, source_id, source_file)
    elif source_file.startswith("Portfolio Performance _ Charles Schwab"):
        parsed = parse_schwab_performance(text, source_id, source_file)
    else:
        source = source_record(
            source_id=source_id,
            source_file=source_file,
            source_kind="unknown",
            institution="Unknown",
            account_key="unknown",
            text=text,
            transactions=[],
            periods=[],
            warnings=[],
        )
        parsed = ParsedSource(
            source,
            [],
            [],
            [warning(source_id, source_file, "unsupported_source", severity="error")],
        )
    parsed.source["source_sha256"] = source_hash
    return parsed


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fetch_market_data(
    tickers: Iterable[str], start: date, end: date, output_dir: Path
) -> dict[str, dict[str, Any]]:
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - environment-specific guard
        raise RuntimeError("yfinance is required unless --skip-market-data is used") from exc

    market_dir = output_dir / "market_data"
    market_dir.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, dict[str, Any]] = {}
    for ticker in sorted(set(tickers)):
        try:
            history = yf.Ticker(ticker).history(
                start=(start - timedelta(days=7)).isoformat(),
                end=(end + timedelta(days=2)).isoformat(),
                interval="1d",
                actions=True,
                auto_adjust=False,
                repair=False,
            )
            if history.empty:
                raise RuntimeError("empty history")
            history = history.reset_index()
            date_column = "Date" if "Date" in history.columns else history.columns[0]
            columns = [
                date_column,
                "Open",
                "High",
                "Low",
                "Close",
                "Adj Close",
                "Volume",
                "Dividends",
                "Stock Splits",
                "Capital Gains",
            ]
            available = [column for column in columns if column in history.columns]
            history[available].to_csv(market_dir / f"{ticker}.csv", index=False)
            metadata[ticker] = {
                "status": "ok",
                "rows": int(len(history)),
                "start": str(history[date_column].iloc[0].date()),
                "end": str(history[date_column].iloc[-1].date()),
                "file": f"market_data/{ticker}.csv",
            }
        except Exception as exc:  # keep the import useful when one ticker is unsupported
            metadata[ticker] = {"status": "unavailable", "error": type(exc).__name__}
    return metadata


def load_adjusted_close_history(output_dir: Path) -> dict[str, dict[str, float]]:
    history: dict[str, dict[str, float]] = {}
    market_dir = output_dir / "market_data"
    if not market_dir.exists():
        return history
    for path in sorted(market_dir.glob("*.csv")):
        series: dict[str, float] = {}
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                raw_date = row.get("Date") or row.get("Datetime") or ""
                raw_price = row.get("Adj Close") or row.get("Close") or ""
                if not raw_date or not raw_price:
                    continue
                try:
                    price = float(raw_price)
                    price_date = date.fromisoformat(raw_date[:10])
                except (TypeError, ValueError):
                    continue
                if price > 0:
                    series[price_date.isoformat()] = price
        if series:
            history[path.stem.upper()] = series
    return history


def transaction_notional(row: dict[str, Any]) -> float:
    amount = parse_decimal(row.get("amount"))
    if amount is not None and amount != 0:
        return float(abs(amount))
    quantity = parse_decimal(row.get("quantity"))
    price = parse_decimal(row.get("unit_price"))
    if quantity is not None and price is not None:
        return float(abs(quantity * price))
    return 0.0


def _weighted_advantage(actions: list[dict[str, Any]]) -> float | None:
    weighted = [
        (float(item["notional"]), float(item["advantage_pct_points"]))
        for item in actions
        if item.get("score_status") == "scored"
        and item.get("advantage_pct_points") is not None
        and float(item.get("notional") or 0) > 0
    ]
    total = sum(notional for notional, _ in weighted)
    if total <= 0:
        return None
    return round(sum(notional * advantage for notional, advantage in weighted) / total, 4)


def _outcome_label(advantage: float | None, deadband: float = 2.0) -> str | None:
    if advantage is None:
        return None
    if advantage > deadband:
        return "ahead"
    if advantage < -deadband:
        return "behind"
    return "similar"


def load_assets_reference(output_dir: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    metadata_path = output_dir / "assets_sheet_source.json"
    notes_path = output_dir / "assets_sheet_action_notes.csv"
    snapshots_path = output_dir / "assets_sheet_snapshots.csv"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else None
    notes: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    if notes_path.exists():
        with notes_path.open(newline="", encoding="utf-8") as handle:
            notes = list(csv.DictReader(handle))
    if snapshots_path.exists():
        with snapshots_path.open(newline="", encoding="utf-8") as handle:
            snapshots = list(csv.DictReader(handle))
    return metadata, notes, snapshots


def build_reconciliation(
    transactions: list[dict[str, Any]],
    assets_metadata: dict[str, Any] | None,
    notes: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    buy_actions = {"buy", "exchange_buy"}
    sell_actions = {"sell", "exchange_sell"}
    ledger_keys = {
        (
            row["effective_date"],
            row["symbol"],
            "buy" if row["action"] in buy_actions else "sell",
        )
        for row in transactions
        if row.get("effective_date")
        and row.get("symbol")
        and row.get("action") in buy_actions | sell_actions
    }
    matched_notes = 0
    completed_notes = 0
    dated_completed_notes = 0
    for note in notes:
        if note.get("note_type") != "reported_completed":
            continue
        completed_notes += 1
        note_date = note.get("inferred_date") or ""
        if note_date:
            dated_completed_notes += 1
        tickers = [ticker for ticker in (note.get("tickers") or "").split(";") if ticker]
        note_text = (note.get("note") or "").lower()
        direction = "buy" if re.search(r"\b(?:buy|bought)\b", note_text) else "sell"
        if note_date and any(
            (note_date, ticker, direction) in ledger_keys for ticker in tickers
        ):
            matched_notes += 1

    ledger_symbols = {row["symbol"] for row in transactions if row.get("symbol")}
    sheet_symbols = {row["symbol"] for row in snapshots if row.get("symbol")}
    return {
        "assets_sheet_available": assets_metadata is not None,
        "assets_sheet_evidence_role": "secondary_unverified" if assets_metadata else None,
        "assets_sheet_source_modified_time": assets_metadata.get("source_modified_time") if assets_metadata else None,
        "snapshot_rows": len(snapshots),
        "action_notes": len(notes),
        "reported_completed_notes": completed_notes,
        "dated_completed_notes": dated_completed_notes,
        "date_symbol_direction_matches_to_pdf_ledger": matched_notes,
        "dated_completed_notes_without_date_symbol_direction_match": max(
            0, dated_completed_notes - matched_notes
        ),
        "symbols_only_in_sheet": sorted(sheet_symbols - ledger_symbols),
        "symbols_only_in_pdf_ledgers": sorted(ledger_symbols - sheet_symbols),
        "interpretation": (
            "The Assets workbook is a secondary planning/snapshot source. Its buy/sell text may be a plan, "
            "and its totals can cover a different account scope. PDF ledger rows take precedence; unmatched "
            "sheet notes are retained as context and are not scored."
        ),
    }


def build_action_quality_artifact(
    output_dir: Path,
    transactions: list[dict[str, Any]],
    periods: list[dict[str, Any]],
    manifest: dict[str, Any],
    benchmark: str,
) -> dict[str, Any]:
    from app.engines.action_quality import AllocationAction, score_actions

    # Recurring plan contributions execute a standing allocation policy. Treating
    # each payroll row as a new discretionary choice would overweight that policy.
    decision_types = {"buy", "sell", "exchange_buy", "exchange_sell"}
    scorable_types = {"buy", "exchange_buy"}
    decision_rows = [row for row in transactions if row["action"] in decision_types]
    allocation_actions = [
        AllocationAction(
            action_id=row["event_id"],
            action_date=row["effective_date"],
            action_type=row["action"],
            ticker=row["symbol"] or None,
            notional=transaction_notional(row),
        )
        for row in decision_rows
    ]
    prices = load_adjusted_close_history(output_dir)
    report = score_actions(
        allocation_actions,
        prices,
        benchmark_ticker=benchmark,
        horizon_days=365,
        as_of=date.today(),
        deadband_pct_points=2.0,
        scorable_action_types=scorable_types,
    ).to_dict()

    row_by_id = {row["event_id"]: row for row in decision_rows}
    enriched_actions: list[dict[str, Any]] = []
    for scored in report["actions"]:
        source = row_by_id[scored["action_id"]]
        scored.update(
            {
                "institution": source["institution"],
                "account_key": source["account_key"],
                "security_name": source["security_name"],
                "source_file": source["source_file"],
                "parse_confidence": source["parse_confidence"],
                "evidence_role": "primary_ledger",
            }
        )
        enriched_actions.append(scored)

    mature = [
        item for item in enriched_actions if item.get("score_status") == "scored" and item.get("maturity") == "mature"
    ]
    developing = [
        item for item in enriched_actions if item.get("score_status") == "scored" and item.get("maturity") == "developing"
    ]
    primary_advantage = _weighted_advantage(mature)
    primary_summary = {
        "basis": "mature 12-month discretionary buy/reallocation actions only",
        "mature_actions": len(mature),
        "developing_actions": len(developing),
        "weighted_advantage_pct_points": primary_advantage,
        "weighted_outcome": _outcome_label(primary_advantage),
        "descriptive_opportunity_cost_non_additive": round(
            sum(float(item.get("opportunity_cost") or 0) for item in mature), 2
        ),
        "interpretation": (
            "Each action asks whether the purchased security beat VFFVX over the same 12-month window. "
            "The opportunity-cost values overlap and must not be treated as a causal portfolio loss."
        ),
    }

    buckets: dict[int, list[dict[str, Any]]] = {}
    for item in enriched_actions:
        if item.get("score_status") != "scored":
            continue
        buckets.setdefault(int(item["action_date"][:4]), []).append(item)
    year_buckets = []
    for year, items in sorted(buckets.items()):
        advantage = _weighted_advantage(items)
        year_buckets.append(
            {
                "year": year,
                "actions": len(items),
                "mature": sum(item.get("maturity") == "mature" for item in items),
                "developing": sum(item.get("maturity") == "developing" for item in items),
                "ahead": sum(item.get("outcome") == "ahead" for item in items),
                "similar": sum(item.get("outcome") == "similar" for item in items),
                "behind": sum(item.get("outcome") == "behind" for item in items),
                "weighted_advantage_pct_points": advantage,
            }
        )

    assets_metadata, notes, snapshots = load_assets_reference(output_dir)
    reconciliation = build_reconciliation(transactions, assets_metadata, notes, snapshots)
    latest_market_date = max(
        (meta.get("end", "") for meta in manifest.get("market_data", {}).values() if meta.get("status") == "ok"),
        default="",
    )
    artifact = {
        "schema_version": 1,
        "available": benchmark in prices,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": {
            "ticker": benchmark,
            "name": "Vanguard Target Retirement 2055 Fund",
            "horizon_days": 365,
            "deadband_pct_points": 2.0,
            "price_field": "adjusted close",
            "market_data_source": "Yahoo Finance via yfinance",
            "as_of_date": latest_market_date,
        },
        "coverage": {
            "source_files": len(manifest.get("sources", [])),
            "ledger_transactions": len(transactions),
            "performance_periods": len(periods),
            "decision_rows": len(decision_rows),
            "buy_like_candidate_rows": sum(
                row["action"] in scorable_types for row in decision_rows
            ),
            "automatic_or_cash_rows_not_treated_as_decisions": len(transactions) - len(decision_rows),
            "date_start": min((row["effective_date"] for row in transactions), default=""),
            "date_end": max((row["effective_date"] for row in transactions), default=""),
        },
        "primary_summary": primary_summary,
        "summary": report["summary"],
        "year_buckets": year_buckets,
        "actions": enriched_actions,
        "reconciliation": reconciliation,
        "limitations": [
            "Outcome is not decision-process quality: taxes, risk, liquidity, intent, and information available at the time are not observed.",
            "VFFVX is an age-specific high-equity glide-path fund and is not a fair alternative for every cash, bond, or plan-constrained decision.",
            "Recurring plan contributions execute a standing allocation policy and are not counted as independent discretionary decisions.",
            "Only dated buy-like rows with a public ticker and price history are scored; sells and unmatched or proprietary plan funds remain unscored.",
            "Adjusted-close returns already include distributions; dividend and reinvestment rows are excluded to avoid double counting.",
        ],
    }
    (output_dir / "action_quality.json").write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return artifact


def build_private_dataset(
    raw_dir: Path,
    output_dir: Path,
    *,
    benchmark: str,
    skip_market_data: bool,
) -> dict[str, Any]:
    pdfs = sorted(raw_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in {raw_dir}")

    parsed_sources = [parse_source(path) for path in pdfs]
    sources = [item.source for item in parsed_sources]
    transactions = [row for item in parsed_sources for row in item.transactions]
    periods = [row for item in parsed_sources for row in item.periods]
    warnings = [row for item in parsed_sources for row in item.warnings]
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        output_dir.chmod(0o700)
        output_dir.parent.chmod(0o700)
    except OSError:
        pass

    write_csv(output_dir / "transactions.csv", transactions, TRANSACTION_FIELDS)
    write_csv(output_dir / "performance_periods.csv", periods, PERFORMANCE_FIELDS)
    write_csv(output_dir / "parse_warnings.csv", warnings, WARNING_FIELDS)

    effective_dates = [parse_us_date(datetime.strptime(row["effective_date"], "%Y-%m-%d").strftime("%m/%d/%Y")) for row in transactions]
    valid_dates = [value for value in effective_dates if value]
    market_metadata: dict[str, dict[str, Any]] = {}
    if not skip_market_data and valid_dates:
        tickers = [row["symbol"] for row in transactions if row["symbol"]]
        tickers.append(benchmark)
        market_metadata = fetch_market_data(
            tickers,
            min(valid_dates),
            date.today(),
            output_dir,
        )

    imported_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": 1,
        "parser_version": PARSER_VERSION,
        "imported_at": imported_at,
        "benchmark": benchmark,
        "privacy": {
            "output_scope": ".private/finance",
            "raw_text_persisted": False,
            "account_identifiers_persisted": False,
            "names_or_addresses_persisted": False,
        },
        "counts": {
            "source_files": len(sources),
            "transactions": len(transactions),
            "performance_periods": len(periods),
            "warnings": len(warnings),
        },
        "market_data": market_metadata,
        "sources": sources,
    }
    artifact = build_action_quality_artifact(
        output_dir,
        transactions,
        periods,
        manifest,
        benchmark,
    )
    manifest["action_quality"] = {
        "available": artifact["available"],
        "file": "action_quality.json",
        "scored_actions": artifact["summary"]["scored_actions"],
        "mature_actions": artifact["primary_summary"]["mature_actions"],
    }
    (output_dir / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_dir", type=Path, help="Directory containing the source PDFs")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--benchmark", default="VFFVX")
    parser.add_argument("--skip-market-data", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    output_dir = require_private_output(args.output_dir)
    manifest = build_private_dataset(
        args.raw_dir.resolve(),
        output_dir,
        benchmark=args.benchmark.upper(),
        skip_market_data=args.skip_market_data,
    )
    counts = manifest["counts"]
    print(
        f"Imported {counts['source_files']} sources, {counts['transactions']} transactions, "
        f"and {counts['performance_periods']} performance periods into {output_dir}"
    )
    if counts["warnings"]:
        print(f"Review {counts['warnings']} parser warnings in parse_warnings.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
