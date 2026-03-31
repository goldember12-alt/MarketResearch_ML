"""Alpha Vantage remote fetch helpers for monthly prices and overview metadata."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from src.data.remote_config import AlphaVantageProviderConfig


class AlphaVantageThrottleError(RuntimeError):
    """Raised when Alpha Vantage reports a throttling or quota condition."""


class AlphaVantageResponseError(RuntimeError):
    """Raised when Alpha Vantage returns an unexpected payload."""


@dataclass(frozen=True)
class AlphaVantageDatasetResult:
    """One fetched Alpha Vantage dataset plus audit details."""

    frame: pd.DataFrame
    completed_symbols: list[str]
    failed_symbols: list[str]
    notes: list[str]
    throttle_detected: bool


def _request_json(
    *,
    base_url: str,
    params: dict[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Issue a JSON request using the Python standard library."""
    url = f"{base_url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "MarketResearch_ML/remote-fetch"})
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise AlphaVantageResponseError("Alpha Vantage returned a non-mapping JSON payload.")
    return payload


def parse_monthly_adjusted_response(
    payload: dict[str, Any],
    *,
    symbol: str,
    identifier_column: str,
    source_function: str,
) -> pd.DataFrame:
    """Convert one Alpha Vantage monthly adjusted payload into a tabular frame."""
    if "Error Message" in payload:
        raise AlphaVantageResponseError(str(payload["Error Message"]))
    if "Note" in payload or "Information" in payload:
        message = str(payload.get("Note") or payload.get("Information"))
        raise AlphaVantageThrottleError(message)

    series = payload.get("Monthly Adjusted Time Series")
    if not isinstance(series, dict) or not series:
        raise AlphaVantageResponseError(
            f"Monthly adjusted payload for {symbol} did not contain 'Monthly Adjusted Time Series'."
        )

    rows: list[dict[str, Any]] = []
    for date_string, raw_values in series.items():
        if not isinstance(raw_values, dict):
            continue
        rows.append(
            {
                identifier_column: symbol,
                "date": date_string,
                "open": raw_values.get("1. open"),
                "high": raw_values.get("2. high"),
                "low": raw_values.get("3. low"),
                "close": raw_values.get("4. close"),
                "adjusted_close": raw_values.get("5. adjusted close"),
                "volume": raw_values.get("6. volume"),
                "dividend_amount": raw_values.get("7. dividend amount"),
                "split_coefficient": raw_values.get("8. split coefficient"),
                "source_provider": "alphavantage",
                "source_function": source_function,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise AlphaVantageResponseError(f"Monthly adjusted payload for {symbol} was empty.")

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
        "dividend_amount",
        "split_coefficient",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = (
        frame.dropna(subset=["date", "adjusted_close"]).sort_values("date").reset_index(drop=True)
    )
    return frame


def parse_overview_response(payload: dict[str, Any], *, symbol: str) -> dict[str, Any]:
    """Convert one Alpha Vantage overview payload into a flat metadata record."""
    if "Error Message" in payload:
        raise AlphaVantageResponseError(str(payload["Error Message"]))
    if "Note" in payload or "Information" in payload:
        message = str(payload.get("Note") or payload.get("Information"))
        raise AlphaVantageThrottleError(message)
    if not payload or "Symbol" not in payload:
        raise AlphaVantageResponseError(f"Overview payload for {symbol} was empty or malformed.")

    return {
        "ticker": symbol,
        "asset_type": payload.get("AssetType"),
        "name": payload.get("Name"),
        "exchange": payload.get("Exchange"),
        "currency": payload.get("Currency"),
        "country": payload.get("Country"),
        "sector": payload.get("Sector"),
        "industry": payload.get("Industry"),
        "market_capitalization_snapshot": payload.get("MarketCapitalization"),
        "pe_ratio_snapshot": payload.get("PERatio"),
        "price_to_sales_snapshot": payload.get("PriceToSalesRatioTTM"),
        "price_to_book_snapshot": payload.get("PriceToBookRatio"),
        "ev_to_ebitda_snapshot": payload.get("EVToEBITDA"),
        "roe_ttm_snapshot": payload.get("ReturnOnEquityTTM"),
        "roa_ttm_snapshot": payload.get("ReturnOnAssetsTTM"),
        "quarterly_revenue_growth_yoy_snapshot": payload.get("QuarterlyRevenueGrowthYOY"),
        "quarterly_earnings_growth_yoy_snapshot": payload.get("QuarterlyEarningsGrowthYOY"),
        "fiscal_year_end": payload.get("FiscalYearEnd"),
        "latest_quarter": payload.get("LatestQuarter"),
        "source_provider": "alphavantage",
        "source_function": "OVERVIEW",
    }


def fetch_monthly_adjusted_series(
    *,
    symbols: list[str],
    identifier_column: str,
    provider: AlphaVantageProviderConfig,
    api_key: str,
) -> AlphaVantageDatasetResult:
    """Fetch monthly adjusted price history for a list of symbols."""
    frames: list[pd.DataFrame] = []
    completed_symbols: list[str] = []
    failed_symbols: list[str] = []
    notes: list[str] = []
    throttle_detected = False

    for index, symbol in enumerate(symbols):
        if index > 0 and provider.request_pause_seconds > 0:
            time.sleep(provider.request_pause_seconds)
        try:
            payload = _request_json(
                base_url=provider.base_url,
                params={
                    "function": provider.monthly_adjusted_function,
                    "symbol": symbol,
                    "apikey": api_key,
                    "datatype": provider.datatype,
                    "outputsize": provider.outputsize,
                },
                timeout_seconds=provider.timeout_seconds,
            )
            frame = parse_monthly_adjusted_response(
                payload,
                symbol=symbol,
                identifier_column=identifier_column,
                source_function=provider.monthly_adjusted_function,
            )
            frames.append(frame)
            completed_symbols.append(symbol)
        except AlphaVantageThrottleError as exc:
            failed_symbols.append(symbol)
            notes.append(f"{symbol}: {exc}")
            throttle_detected = True
            break
        except Exception as exc:  # noqa: BLE001
            failed_symbols.append(symbol)
            notes.append(f"{symbol}: {exc}")

    if not frames:
        return AlphaVantageDatasetResult(
            frame=pd.DataFrame(),
            completed_symbols=completed_symbols,
            failed_symbols=failed_symbols,
            notes=notes,
            throttle_detected=throttle_detected,
        )

    combined = pd.concat(frames, ignore_index=True).sort_values([identifier_column, "date"])
    return AlphaVantageDatasetResult(
        frame=combined.reset_index(drop=True),
        completed_symbols=completed_symbols,
        failed_symbols=failed_symbols,
        notes=notes,
        throttle_detected=throttle_detected,
    )


def fetch_overview_metadata(
    *,
    symbols: list[str],
    provider: AlphaVantageProviderConfig,
    api_key: str,
) -> AlphaVantageDatasetResult:
    """Fetch overview metadata for a list of symbols."""
    rows: list[dict[str, Any]] = []
    completed_symbols: list[str] = []
    failed_symbols: list[str] = []
    notes: list[str] = []
    throttle_detected = False

    for index, symbol in enumerate(symbols):
        if index > 0 and provider.request_pause_seconds > 0:
            time.sleep(provider.request_pause_seconds)
        try:
            payload = _request_json(
                base_url=provider.base_url,
                params={
                    "function": provider.overview_function,
                    "symbol": symbol,
                    "apikey": api_key,
                },
                timeout_seconds=provider.timeout_seconds,
            )
            rows.append(parse_overview_response(payload, symbol=symbol))
            completed_symbols.append(symbol)
        except AlphaVantageThrottleError as exc:
            failed_symbols.append(symbol)
            notes.append(f"{symbol}: {exc}")
            throttle_detected = True
            break
        except Exception as exc:  # noqa: BLE001
            failed_symbols.append(symbol)
            notes.append(f"{symbol}: {exc}")

    frame = pd.DataFrame(rows)
    if not frame.empty:
        numeric_columns = [
            "market_capitalization_snapshot",
            "pe_ratio_snapshot",
            "price_to_sales_snapshot",
            "price_to_book_snapshot",
            "ev_to_ebitda_snapshot",
            "roe_ttm_snapshot",
            "roa_ttm_snapshot",
            "quarterly_revenue_growth_yoy_snapshot",
            "quarterly_earnings_growth_yoy_snapshot",
        ]
        for column in numeric_columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame["latest_quarter"] = pd.to_datetime(frame["latest_quarter"], errors="coerce")

    return AlphaVantageDatasetResult(
        frame=frame.reset_index(drop=True),
        completed_symbols=completed_symbols,
        failed_symbols=failed_symbols,
        notes=notes,
        throttle_detected=throttle_detected,
    )
