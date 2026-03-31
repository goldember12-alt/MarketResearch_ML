"""SEC Company Facts fetch and conservative mapping helpers."""

from __future__ import annotations

import gzip
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd

from src.data.remote_config import SecProviderConfig

ALLOWED_SEC_FORMS = {
    "10-Q",
    "10-Q/A",
    "10-K",
    "10-K/A",
    "20-F",
    "20-F/A",
    "40-F",
    "40-F/A",
}
QUARTERLY_FRAME_PATTERN = re.compile(r"Q[1-4]")

INSTANT_FACT_CONCEPTS: dict[str, tuple[str, ...]] = {
    "assets": ("Assets",),
    "equity": (
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "StockholdersEquity",
    ),
    "current_assets": ("AssetsCurrent",),
    "current_liabilities": ("LiabilitiesCurrent",),
    "total_debt": (
        "DebtLongtermAndShorttermCombinedAmount",
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebtNoncurrent",
        "LongTermDebt",
    ),
}

DURATION_FACT_CONCEPTS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "eps_diluted": ("EarningsPerShareDiluted",),
}


class SecResponseError(RuntimeError):
    """Raised when SEC responses are missing required content."""


@dataclass(frozen=True)
class SecCompanyFactsResult:
    """One fetched SEC dataset bundle."""

    mapped_fundamentals: pd.DataFrame
    raw_payloads: dict[str, dict[str, Any]]
    completed_symbols: list[str]
    failed_symbols: list[str]
    notes: list[str]


def _frame_date_span(frame: pd.DataFrame, date_column: str) -> tuple[str | None, str | None]:
    """Return an ISO min/max date span for one fetched frame."""
    if frame.empty or date_column not in frame.columns:
        return None, None
    parsed = pd.to_datetime(frame[date_column], errors="coerce").dropna()
    if parsed.empty:
        return None, None
    return parsed.min().date().isoformat(), parsed.max().date().isoformat()


def resolve_sec_user_agent(*, provider: SecProviderConfig, environment: dict[str, str]) -> str:
    """Resolve a SEC-compatible user agent from environment variables only."""
    explicit = environment.get(provider.user_agent_env_var, "").strip()
    if explicit:
        return explicit
    contact_email = environment.get(provider.contact_email_env_var, "").strip()
    if contact_email:
        return f"{provider.app_name} ({contact_email})"
    raise ValueError(
        "SEC remote fetch requires either "
        f"{provider.user_agent_env_var} or {provider.contact_email_env_var} to be set."
    )


def _request_json(
    *,
    url: str,
    timeout_seconds: float,
    user_agent: str,
) -> dict[str, Any]:
    """Issue a SEC JSON request using the standard library."""
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        raw_bytes = response.read()
        content_encoding = response.headers.get("Content-Encoding")
        payload = json.loads(_decode_response_bytes(raw_bytes, content_encoding=content_encoding))
    if not isinstance(payload, dict):
        raise SecResponseError("SEC returned a non-mapping JSON payload.")
    return payload


def _decode_response_bytes(raw_bytes: bytes, *, content_encoding: str | None) -> str:
    """Decode SEC response bytes, including gzip-compressed payloads."""
    normalized_encoding = (content_encoding or "").lower()
    if "gzip" in normalized_encoding or raw_bytes.startswith(b"\x1f\x8b"):
        raw_bytes = gzip.decompress(raw_bytes)
    return raw_bytes.decode("utf-8")


def build_ticker_cik_map(payload: dict[str, Any]) -> dict[str, str]:
    """Build a ticker-to-zero-padded-CIK mapping from SEC's company tickers file."""
    mapping: dict[str, str] = {}
    for entry in payload.values():
        if not isinstance(entry, dict):
            continue
        ticker = str(entry.get("ticker", "")).upper().strip()
        cik_number = entry.get("cik_str")
        if not ticker or cik_number in {None, ""}:
            continue
        mapping[ticker] = f"{int(cik_number):010d}"
    return mapping


def _extract_fact_series(
    payload: dict[str, Any],
    *,
    concept_names: tuple[str, ...],
    instant: bool,
) -> pd.DataFrame:
    """Extract a best-effort concept series from SEC Company Facts."""
    facts = payload.get("facts", {})
    us_gaap = facts.get("us-gaap", {})
    if not isinstance(us_gaap, dict):
        return pd.DataFrame()

    for concept_name in concept_names:
        concept_payload = us_gaap.get(concept_name)
        if not isinstance(concept_payload, dict):
            continue
        units = concept_payload.get("units", {})
        if not isinstance(units, dict):
            continue
        for unit_name, observations in units.items():
            if not isinstance(observations, list):
                continue
            rows: list[dict[str, Any]] = []
            for observation in observations:
                if not isinstance(observation, dict):
                    continue
                form = str(observation.get("form", "")).upper()
                if form not in ALLOWED_SEC_FORMS:
                    continue
                frame = str(observation.get("frame", "") or "")
                if instant:
                    if observation.get("end") in {None, ""}:
                        continue
                else:
                    if observation.get("end") in {None, ""} or observation.get("start") in {
                        None,
                        "",
                    }:
                        continue
                    fp = str(observation.get("fp", "")).upper()
                    if fp not in {"Q1", "Q2", "Q3", "Q4"} and not QUARTERLY_FRAME_PATTERN.search(
                        frame
                    ):
                        continue
                rows.append(
                    {
                        "report_date": pd.to_datetime(observation.get("end"), errors="coerce"),
                        "filing_date": pd.to_datetime(observation.get("filed"), errors="coerce"),
                        "value": observation.get("val"),
                        "unit": unit_name,
                        "form": form,
                        "frame": frame or None,
                        "concept": concept_name,
                    }
                )
            if not rows:
                continue
            frame = pd.DataFrame(rows).dropna(subset=["report_date", "value"])
            if frame.empty:
                continue
            frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
            frame = frame.dropna(subset=["value"])
            if frame.empty:
                continue
            frame = frame.sort_values(["report_date", "filing_date"])
            frame = frame.drop_duplicates(subset=["report_date"], keep="first").reset_index(
                drop=True
            )
            return frame
    return pd.DataFrame()


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Compute a ratio while guarding against divide-by-zero."""
    denominator = denominator.where(denominator != 0)
    return numerator / denominator


def map_companyfacts_to_quarterly_fundamentals(
    payload: dict[str, Any],
    *,
    ticker: str,
    sector: str | None = None,
    industry: str | None = None,
) -> pd.DataFrame:
    """Map SEC Company Facts into a conservative quarterly subset for the repo schema."""
    extracted: dict[str, pd.DataFrame] = {}
    for metric_name, concept_names in INSTANT_FACT_CONCEPTS.items():
        extracted[metric_name] = _extract_fact_series(
            payload,
            concept_names=concept_names,
            instant=True,
        )
    for metric_name, concept_names in DURATION_FACT_CONCEPTS.items():
        extracted[metric_name] = _extract_fact_series(
            payload,
            concept_names=concept_names,
            instant=False,
        )

    non_empty_series = [frame for frame in extracted.values() if not frame.empty]
    if not non_empty_series:
        return pd.DataFrame()

    report_dates = sorted(
        {
            pd.Timestamp(report_date)
            for frame in non_empty_series
            for report_date in frame["report_date"].tolist()
        }
    )
    fundamentals = pd.DataFrame({"report_date": report_dates})
    for metric_name, series in extracted.items():
        if series.empty:
            continue
        metric_frame = series.rename(
            columns={
                "value": metric_name,
                "filing_date": f"{metric_name}_filing_date",
                "concept": f"{metric_name}_concept",
                "form": f"{metric_name}_form",
            }
        )[
            [
                "report_date",
                metric_name,
                f"{metric_name}_filing_date",
                f"{metric_name}_concept",
                f"{metric_name}_form",
            ]
        ]
        fundamentals = fundamentals.merge(metric_frame, on="report_date", how="left")

    filing_columns = [column for column in fundamentals.columns if column.endswith("_filing_date")]
    if filing_columns:
        fundamentals["filing_date"] = fundamentals[filing_columns].max(axis=1)
    else:
        fundamentals["filing_date"] = pd.NaT

    fundamentals["ticker"] = ticker
    fundamentals["sector"] = sector
    fundamentals["industry"] = industry
    fundamentals["market_cap"] = pd.NA
    fundamentals["pe_ratio"] = pd.NA
    fundamentals["price_to_sales"] = pd.NA
    fundamentals["price_to_book"] = pd.NA
    fundamentals["ev_to_ebitda"] = pd.NA
    fundamentals["gross_margin"] = _safe_ratio(
        fundamentals.get("gross_profit", pd.Series(dtype=float)),
        fundamentals.get("revenue", pd.Series(dtype=float)),
    )
    fundamentals["operating_margin"] = _safe_ratio(
        fundamentals.get("operating_income", pd.Series(dtype=float)),
        fundamentals.get("revenue", pd.Series(dtype=float)),
    )
    fundamentals["roe"] = _safe_ratio(
        fundamentals.get("net_income", pd.Series(dtype=float)),
        fundamentals.get("equity", pd.Series(dtype=float)),
    )
    fundamentals["roa"] = _safe_ratio(
        fundamentals.get("net_income", pd.Series(dtype=float)),
        fundamentals.get("assets", pd.Series(dtype=float)),
    )
    fundamentals["revenue_growth"] = fundamentals.get("revenue", pd.Series(dtype=float)).pct_change(
        4
    )
    fundamentals["eps_growth"] = fundamentals.get("eps_diluted", pd.Series(dtype=float)).pct_change(
        4
    )
    fundamentals["debt_to_equity"] = _safe_ratio(
        fundamentals.get("total_debt", pd.Series(dtype=float)),
        fundamentals.get("equity", pd.Series(dtype=float)),
    )
    fundamentals["current_ratio"] = _safe_ratio(
        fundamentals.get("current_assets", pd.Series(dtype=float)),
        fundamentals.get("current_liabilities", pd.Series(dtype=float)),
    )
    fundamentals["source_provider"] = "sec"
    fundamentals["source_endpoint"] = "companyfacts"
    fundamentals["filing_date"] = pd.to_datetime(fundamentals["filing_date"], errors="coerce")
    fundamentals["report_date"] = pd.to_datetime(fundamentals["report_date"], errors="coerce")

    ordered_columns = [
        "ticker",
        "report_date",
        "filing_date",
        "sector",
        "industry",
        "market_cap",
        "pe_ratio",
        "price_to_sales",
        "price_to_book",
        "ev_to_ebitda",
        "gross_margin",
        "operating_margin",
        "roe",
        "roa",
        "revenue_growth",
        "eps_growth",
        "debt_to_equity",
        "current_ratio",
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
        "eps_diluted",
        "assets",
        "equity",
        "current_assets",
        "current_liabilities",
        "total_debt",
        "source_provider",
        "source_endpoint",
    ]
    concept_columns = [column for column in fundamentals.columns if column.endswith("_concept")]
    form_columns = [column for column in fundamentals.columns if column.endswith("_form")]
    ordered_columns.extend(sorted(concept_columns))
    ordered_columns.extend(sorted(form_columns))
    return fundamentals[ordered_columns].sort_values("report_date").reset_index(drop=True)


def fetch_sec_companyfacts(
    *,
    tickers: list[str],
    provider: SecProviderConfig,
    user_agent: str,
    metadata: pd.DataFrame | None = None,
    logger: logging.Logger | None = None,
    dataset_name: str = "fundamentals_sec_companyfacts",
    fetch_run_id: str | None = None,
) -> SecCompanyFactsResult:
    """Fetch SEC Company Facts payloads and map them into a conservative subset."""
    if logger is not None:
        logger.info(
            "fetch_reference_start run_id=%s provider=sec dataset=%s resource=company_tickers url=%s",
            fetch_run_id,
            dataset_name,
            provider.company_tickers_url,
        )
    ticker_payload = _request_json(
        url=provider.company_tickers_url,
        timeout_seconds=provider.timeout_seconds,
        user_agent=user_agent,
    )
    ticker_cik_map = build_ticker_cik_map(ticker_payload)
    if logger is not None:
        logger.info(
            "fetch_reference_complete run_id=%s provider=sec dataset=%s resource=company_tickers mapped_ticker_count=%s",
            fetch_run_id,
            dataset_name,
            len(ticker_cik_map),
        )
    metadata_lookup: dict[str, dict[str, Any]] = {}
    if metadata is not None and not metadata.empty:
        metadata_lookup = (
            metadata[["ticker", "sector", "industry"]]
            .drop_duplicates(subset=["ticker"])
            .set_index("ticker")
            .to_dict(orient="index")
        )

    mapped_frames: list[pd.DataFrame] = []
    raw_payloads: dict[str, dict[str, Any]] = {}
    completed_symbols: list[str] = []
    failed_symbols: list[str] = []
    notes: list[str] = []

    for index, ticker in enumerate(tickers):
        if index > 0 and provider.request_pause_seconds > 0:
            if logger is not None:
                logger.info(
                    "fetch_sleep run_id=%s provider=sec dataset=%s seconds=%.2f next_symbol=%s",
                    fetch_run_id,
                    dataset_name,
                    provider.request_pause_seconds,
                    ticker,
                )
            time.sleep(provider.request_pause_seconds)
        symbol_started = time.perf_counter()
        if logger is not None:
            logger.info(
                "fetch_symbol_start run_id=%s provider=sec dataset=%s symbol=%s symbol_index=%s symbol_total=%s",
                fetch_run_id,
                dataset_name,
                ticker,
                index + 1,
                len(tickers),
            )
        cik = ticker_cik_map.get(ticker.upper())
        if cik is None:
            failed_symbols.append(ticker)
            notes.append(f"{ticker}: SEC ticker-to-CIK lookup did not include this symbol.")
            elapsed_seconds = time.perf_counter() - symbol_started
            if logger is not None:
                logger.warning(
                    "fetch_symbol_failed run_id=%s provider=sec dataset=%s symbol=%s elapsed_seconds=%.3f exception=%s",
                    fetch_run_id,
                    dataset_name,
                    ticker,
                    elapsed_seconds,
                    "SEC ticker-to-CIK lookup did not include this symbol.",
                )
            continue
        try:
            url = provider.company_facts_base_url.format(cik=cik)
            payload = _request_json(
                url=url,
                timeout_seconds=provider.timeout_seconds,
                user_agent=user_agent,
            )
            raw_payloads[ticker] = payload
            sector = metadata_lookup.get(ticker, {}).get("sector")
            industry = metadata_lookup.get(ticker, {}).get("industry")
            mapped = map_companyfacts_to_quarterly_fundamentals(
                payload,
                ticker=ticker,
                sector=sector,
                industry=industry,
            )
            if not mapped.empty:
                mapped_frames.append(mapped)
                min_date, max_date = _frame_date_span(mapped, "report_date")
                if logger is not None:
                    logger.info(
                        "fetch_symbol_complete run_id=%s provider=sec dataset=%s symbol=%s cik=%s elapsed_seconds=%.3f row_count=%s min_date=%s max_date=%s",
                        fetch_run_id,
                        dataset_name,
                        ticker,
                        cik,
                        time.perf_counter() - symbol_started,
                        len(mapped),
                        min_date,
                        max_date,
                    )
            elif logger is not None:
                logger.warning(
                    "fetch_symbol_no_rows run_id=%s provider=sec dataset=%s symbol=%s cik=%s elapsed_seconds=%.3f",
                    fetch_run_id,
                    dataset_name,
                    ticker,
                    cik,
                    time.perf_counter() - symbol_started,
                )
            completed_symbols.append(ticker)
        except Exception as exc:  # noqa: BLE001
            failed_symbols.append(ticker)
            notes.append(f"{ticker}: {exc}")
            if logger is not None:
                logger.exception(
                    "fetch_symbol_failed run_id=%s provider=sec dataset=%s symbol=%s cik=%s elapsed_seconds=%.3f exception=%s",
                    fetch_run_id,
                    dataset_name,
                    ticker,
                    cik,
                    time.perf_counter() - symbol_started,
                    exc,
                )

    combined = (
        pd.concat(mapped_frames, ignore_index=True).sort_values(["ticker", "report_date"])
        if mapped_frames
        else pd.DataFrame()
    )
    if combined.empty and logger is not None:
        logger.warning(
            "fetch_dataset_empty run_id=%s provider=sec dataset=%s completed_symbols=%s failed_symbols=%s",
            fetch_run_id,
            dataset_name,
            completed_symbols,
            failed_symbols,
        )
    return SecCompanyFactsResult(
        mapped_fundamentals=combined.reset_index(drop=True),
        raw_payloads=raw_payloads,
        completed_symbols=completed_symbols,
        failed_symbols=failed_symbols,
        notes=notes,
    )
