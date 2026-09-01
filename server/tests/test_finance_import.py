"""Synthetic regression tests for the private finance importers.

The fixtures in this module are deliberately fabricated.  They exercise the
statement layouts without reading anything from ``.private`` or the user's raw
finance directory.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
PRIVATE_NAME_MARKER = "PRIVATE-HOLDER-ZEPHYR"
PRIVATE_ACCOUNT_MARKER = "ACCT-SECRET-90817263"


def _load_script(module_name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses inspect sys.modules while their class decorators run.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


finance = _load_script("finance_history_import_for_tests", "import_finance_history.py")
assets = _load_script("assets_sheet_import_for_tests", "import_assets_sheet.py")


def test_cli_output_guards_reject_trackable_locations():
    assert finance.require_private_output(finance.DEFAULT_OUTPUT_DIR) == finance.DEFAULT_OUTPUT_DIR
    assert assets.require_private_output(assets.DEFAULT_OUTPUT_DIR) == assets.DEFAULT_OUTPUT_DIR

    trackable = finance.REPO_ROOT / "finance-export"
    with pytest.raises(ValueError, match="inside the repository's .private"):
        finance.require_private_output(trackable)
    with pytest.raises(ValueError, match="inside the repository's .private"):
        assets.require_private_output(trackable)


def _roth_line(
    *,
    settlement: str = "01/04/2024",
    trade: str = "01/03/2024",
    symbol: str = "SYNTH",
    name: str = "Synthetic Index Fund",
    action: str = "Buy",
    bucket: str = "Brokerage",
    quantity: str = "2.500",
    price: str = "$40.00",
    fees: str = "$0.00",
    amount: str = "$100.00",
) -> str:
    prefix = f"{settlement} {trade} {symbol}"
    return (
        f"{prefix:<40}"
        f"{name:<47}"
        f"{action:<19}"
        f"{bucket:<10}"
        f"{quantity:>15}"
        f"{price:>12}"
        f"{fees:>19}"
        f"{amount:>12}"
    )


def _roth_continuation(*, name: str = "", action: str = "") -> str:
    return f"{'':40}{name:<47}{action:<19}"


def _vanguard_plan_line(
    *,
    trade: str,
    symbol: str,
    name: str,
    action: str,
    action_start: int,
    quantity: str,
    price: str,
    fees: str,
    amount: str,
) -> str:
    offset = action_start - 81
    name_start = 38 + offset
    account_start = 61 + offset
    prefix = f"{trade} {symbol}"
    assert len(prefix) <= name_start
    line = prefix.ljust(name_start)
    line += name.ljust(account_start - name_start)
    line += "Retirement".ljust(action_start - account_start)
    line += action
    line += f" {quantity} {price} {fees} {amount}"
    assert line.index(action) == action_start
    return line


def test_money_and_date_parsing_handles_statement_conventions():
    assert finance.parse_decimal("$1,234.56") == Decimal("1234.56")
    assert finance.parse_decimal("(1,234.56)") == Decimal("-1234.56")
    assert finance.parse_decimal("+$12.50") == Decimal("12.50")
    assert finance.parse_decimal("Free") == Decimal("0")
    assert finance.parse_decimal("-") is None
    assert finance.parse_decimal("—") is None
    assert finance.parse_decimal("not a number") is None

    assert finance.parse_us_date("01/02/2024") == date(2024, 1, 2)
    assert finance.parse_us_date("Jan 2, 2024") == date(2024, 1, 2)
    assert finance.parse_us_date("January 2, 2024") == date(2024, 1, 2)
    assert finance.parse_us_date("2024-01-02") is None

    assert assets.parse_number("$2,500") == Decimal("2500")
    assert assets.parse_number("(25.5)") == Decimal("-25.5")
    assert assets.parse_number(True) is None
    assert assets.parse_date_text("01/02/24") == date(2024, 1, 2)
    assert assets.parse_date_text("Bought Jan 2", year_context=2024) == date(2024, 1, 2)


def test_roth_wrapped_conversion_parses_free_fee_dash_amount_and_derived_fields():
    text = "\n".join(
        [
            PRIVATE_NAME_MARKER,
            f"Account {PRIVATE_ACCOUNT_MARKER}",
            _roth_line(action="Conversion", fees="Free", amount="—"),
            _roth_continuation(action="(incoming)"),
        ]
    )

    parsed = finance.parse_roth_ledger(text, "source-synthetic", "roth-ledger.pdf")

    assert parsed.warnings == []
    assert len(parsed.transactions) == 1
    row = parsed.transactions[0]
    assert row["trade_date"] == "2024-01-03"
    assert row["settlement_date"] == "2024-01-04"
    assert row["effective_date"] == "2024-01-03"
    assert row["action_raw"] == "Conversion (incoming)"
    assert row["action"] == "conversion"
    assert row["decision_kind"] == "external_flow"
    assert row["symbol"] == "SYNTH"
    assert row["quantity"] == "2.500"
    assert row["unit_price"] == "40.00"
    assert row["fees_raw"] == "Free"
    assert row["fees"] == "0"
    assert row["amount_raw"] == "—"
    assert row["amount"] == ""
    assert row["units_delta"] == "2.500"
    assert row["cash_effect"] == ""
    assert row["external_flow"] == ""
    assert row["parse_confidence"] == "high"

    persisted_shape = json.dumps(
        {"source": parsed.source, "transactions": parsed.transactions, "warnings": parsed.warnings},
        sort_keys=True,
    )
    assert PRIVATE_NAME_MARKER not in persisted_shape
    assert PRIVATE_ACCOUNT_MARKER not in persisted_shape


def test_vanguard_plan_symbol_and_action_columns_support_normal_and_shifted_rows():
    normal = _vanguard_plan_line(
        trade="02/01/2024",
        symbol="VTI",
        name="US Total Market",
        action="Plan Contribution",
        action_start=81,
        quantity="1.250",
        price="$20.00",
        fees="$0.00",
        amount="$25.00",
    )
    shifted = _vanguard_plan_line(
        trade="02/02/2024",
        symbol="VXUS",
        name="International Market",
        action="Fund to Fund Out",
        action_start=79,
        quantity="3.000",
        price="$30.00",
        fees="$0.00",
        amount="$90.00",
    )

    parsed = finance.parse_vanguard_plan_ledger(
        f"{normal}\n{shifted}", "source-synthetic", "plan-ledger.pdf"
    )

    assert parsed.warnings == []
    assert len(parsed.transactions) == 2
    contributed, exchanged_out = parsed.transactions
    assert (contributed["symbol"], contributed["security_name"]) == ("VTI", "US Total Market")
    assert contributed["action"] == "contribution"
    assert contributed["decision_kind"] == "contribution"
    assert contributed["units_delta"] == "1.250"
    assert contributed["cash_effect"] == ""
    assert contributed["external_flow"] == "25.00"

    assert (exchanged_out["symbol"], exchanged_out["security_name"]) == (
        "VXUS",
        "International Market",
    )
    assert exchanged_out["action"] == "exchange_sell"
    assert exchanged_out["decision_kind"] == "reallocation"
    assert exchanged_out["units_delta"] == "-3.000"
    assert exchanged_out["cash_effect"] == ""
    assert exchanged_out["external_flow"] == ""


def test_cash_effect_uses_canonical_account_cash_signs():
    buy = finance.canonical_transaction(
        source_id="source-synthetic",
        source_file="ledger.pdf",
        source_page=1,
        source_row=1,
        institution="Synthetic",
        account_key="synthetic-account",
        account_bucket="Brokerage",
        trade_date=date(2024, 1, 2),
        settlement_date=None,
        action_raw="Buy",
        action="buy",
        decision_kind="trade",
        symbol="SYNTH",
        security_name="Synthetic Fund",
        quantity_raw="2",
        price_raw="50",
        fees_raw="0",
        amount_raw="100",
        confidence="high",
    )
    sell = finance.canonical_transaction(
        source_id="source-synthetic",
        source_file="ledger.pdf",
        source_page=1,
        source_row=2,
        institution="Synthetic",
        account_key="synthetic-account",
        account_bucket="Brokerage",
        trade_date=date(2024, 1, 3),
        settlement_date=None,
        action_raw="Sell",
        action="sell",
        decision_kind="trade",
        symbol="SYNTH",
        security_name="Synthetic Fund",
        quantity_raw="2",
        price_raw="50",
        fees_raw="0",
        amount_raw="100",
        confidence="high",
    )

    assert buy["amount"] == "100"
    assert buy["cash_effect"] == "-100"
    assert sell["amount"] == "100"
    assert sell["cash_effect"] == "100"


def test_standing_contributions_are_not_scored_as_repeated_decisions(tmp_path: Path):
    market_dir = tmp_path / "market_data"
    market_dir.mkdir()
    for ticker, ending_price in (("SYNTH", "110"), ("VFFVX", "105")):
        (market_dir / f"{ticker}.csv").write_text(
            f"Date,Adj Close\n2024-01-02,100\n2025-01-01,{ending_price}\n",
            encoding="utf-8",
        )

    base = {
        "effective_date": "2024-01-02",
        "symbol": "SYNTH",
        "amount": "100",
        "quantity": "1",
        "unit_price": "100",
        "institution": "Synthetic",
        "account_key": "synthetic-account",
        "security_name": "Synthetic Fund",
        "source_file": "synthetic.pdf",
        "parse_confidence": "high",
    }
    transactions = [
        {**base, "event_id": "discretionary-buy", "action": "buy"},
        {**base, "event_id": "standing-contribution", "action": "contribution"},
    ]
    manifest = {
        "sources": [{"source_id": "synthetic"}],
        "market_data": {
            "SYNTH": {"status": "ok", "end": "2025-01-01"},
            "VFFVX": {"status": "ok", "end": "2025-01-01"},
        },
    }

    artifact = finance.build_action_quality_artifact(
        tmp_path, transactions, [], manifest, "VFFVX"
    )

    assert artifact["coverage"]["decision_rows"] == 1
    assert artifact["coverage"]["buy_like_candidate_rows"] == 1
    assert artifact["summary"]["scored_actions"] == 1
    assert [action["action_id"] for action in artifact["actions"]] == ["discretionary-buy"]


def test_sheet_reconciliation_requires_matching_direction():
    transactions = [
        {"effective_date": "2024-01-02", "symbol": "SYNTH", "action": "buy"}
    ]
    sold_note = {
        "note_type": "reported_completed",
        "inferred_date": "2024-01-02",
        "tickers": "SYNTH",
        "note": "Sold SYNTH",
    }
    bought_note = {**sold_note, "note": "Bought SYNTH"}

    mismatch = finance.build_reconciliation(transactions, {}, [sold_note], [])
    match = finance.build_reconciliation(transactions, {}, [bought_note], [])

    assert mismatch["date_symbol_direction_matches_to_pdf_ledger"] == 0
    assert match["date_symbol_direction_matches_to_pdf_ledger"] == 1


def test_fidelity_duplicate_compact_and_detailed_period_keeps_complete_copy():
    text = "\n".join(
        [
            "Beginning Account Value as of Jan 1, 2024 $1,000.00",
            "Ending Account Value as of Dec 31, 2024 $1,200.00",
            "Compact account overview",
            "Beginning Account Value as of Jan 1, 2024 $1,000.00",
            "Deposits $100.00",
            "Withdrawals $10.00",
            "Securities Transferred In $50.00",
            "Securities Transferred Out $5.00",
            "Transaction Costs, Fees & Charges $2.00",
            "Change in Investment Value * $67.00",
            "Ending Account Value as of Dec 31, 2024 $1,200.00",
            "Total Account Return for the period: 12.34%",
        ]
    )

    parsed = finance.parse_fidelity_statement(text, "source-synthetic", "statement.pdf")

    assert parsed.warnings == []
    assert len(parsed.periods) == 1
    period = parsed.periods[0]
    assert period["period_start"] == "2024-01-01"
    assert period["period_end"] == "2024-12-31"
    assert period["beginning_value"] == "1000.00"
    assert period["ending_value"] == "1200.00"
    assert period["external_contributions"] == "100.00"
    assert period["withdrawals"] == "10.00"
    assert period["transfers_in"] == "50.00"
    assert period["transfers_out"] == "5.00"
    assert period["fees"] == "2.00"
    assert period["investment_gain_loss"] == "67.00"
    assert period["personal_return_pct"] == "12.34"
    assert parsed.source["parsed_row_count"] == 1


def test_assets_payload_classifies_snapshots_and_action_notes_without_raw_identity(tmp_path: Path):
    formatted = [
        ["Jan 15", ""],
        ["Symbol", "Value"],
        ["VTI", "$12.5"],
        ["Total", "$12.5"],
        ["", ""],
        ["Bought VXUS Jan 15", "Sell BND"],
        [PRIVATE_NAME_MARKER, PRIVATE_ACCOUNT_MARKER],
    ]
    values = [
        ["Jan 15", ""],
        ["Symbol", "Value"],
        ["VTI", 12.5],
        ["Total", 12.5],
        ["", ""],
        ["Bought VXUS Jan 15", "Sell BND"],
        [PRIVATE_NAME_MARKER, PRIVATE_ACCOUNT_MARKER],
    ]
    payload = {
        "spreadsheet_id": "synthetic-sheet-id",
        "title": "Assets",
        "owner_name": PRIVATE_NAME_MARKER,
        "account_number": PRIVATE_ACCOUNT_MARKER,
        "tabs": [
            {
                "title": "2025",
                "formatted_values": formatted,
                "unformatted_values": values,
            }
        ],
    }

    metadata = assets.import_payload(payload, tmp_path)

    assert metadata["raw_grid_persisted"] is False
    assert metadata["counts"] == {
        "tabs_read": 1,
        "snapshot_rows": 1,
        "action_notes": 2,
        "timeline_rows": 0,
    }
    with (tmp_path / "assets_sheet_snapshots.csv").open(newline="", encoding="utf-8") as handle:
        snapshots = list(csv.DictReader(handle))
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot["snapshot_date"] == "2025-01-15"
    assert snapshot["symbol"] == "VTI"
    assert snapshot["value_unit"] == "USD thousands (sheet convention)"
    assert Decimal(snapshot["market_value_usd"]) == Decimal("12500")
    assert snapshot["evidence_role"] == "secondary_unverified"

    with (tmp_path / "assets_sheet_action_notes.csv").open(newline="", encoding="utf-8") as handle:
        notes = list(csv.DictReader(handle))
    by_ticker = {note["tickers"]: note for note in notes}
    assert by_ticker["VXUS"]["note_type"] == "reported_completed"
    assert by_ticker["VXUS"]["inferred_date"] == "2025-01-15"
    assert by_ticker["VXUS"]["parse_confidence"] == "medium"
    assert by_ticker["BND"]["note_type"] == "planned_or_ambiguous"
    assert by_ticker["BND"]["inferred_date"] == ""
    assert by_ticker["BND"]["parse_confidence"] == "low"

    serialized_outputs = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(tmp_path.iterdir()) if path.is_file()
    )
    assert PRIVATE_NAME_MARKER not in serialized_outputs
    assert PRIVATE_ACCOUNT_MARKER not in serialized_outputs
