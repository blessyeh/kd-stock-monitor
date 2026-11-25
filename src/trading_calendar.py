#!/usr/bin/env python3
"""
Trading Calendar — Taiwan stock market trading-day helpers.

Confirmed limitation (tested 2026-11-25): TWSE's holiday-schedule OpenAPI
(https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule) only ever
serves the MOST RECENTLY ANNOUNCED calendar year — it returned 民國116年
(2027) on that date, with no year/date query parameter that changes that.
It is not a queryable historical database, so this module cannot fetch an
arbitrary past year's holiday list on demand.

Design, given that limitation:
  1. Whenever fetch_and_cache_holiday_schedule() is called, it saves
     whatever year the live API currently serves to
     data/trading_calendar_<year>.json — so each year's official list gets
     captured once it becomes available, and future runs don't need the
     live API again for that year.
  2. is_holiday()/most_recent_trading_day() read ONLY from those cached
     files plus the weekend rule. For a year with no cached file yet, they
     fall back to "weekday = trading day" and log that the result is
     unconfirmed for ad hoc holidays (e.g. typhoon days) — never guess a
     full year's public holidays from memory.
  3. For "what was the last COMPLETE trading day for a report that's
     already been fetched", prefer probing the actual data source instead
     of this calendar — see fetcher.py's _fetch_twse_latest(), which walks
     backward one real day at a time until TWSE actually has data for it.
     That approach is strictly more reliable than any calendar (it can't
     be wrong about an unannounced ad hoc holiday) and is already used
     throughout fetcher.py. This module exists for the cases that
     genuinely need a calendar answer independent of any single data
     source (e.g. backfill date ranges, "is 12/25 a trading day").

Known-confirmed 2026 (民國115年) holidays from 2026-11-25 onward (verified
against TWSE's official announcement, not guessed): only 12/25 (行憲紀念日,
Friday). Earlier-2026 dates are NOT seeded here from memory — only dates
actually captured via fetch_and_cache_holiday_schedule() or explicitly
confirmed are trusted.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Set

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Confirmed (not guessed) remaining 2026 holidays — see module docstring.
_CONFIRMED_HOLIDAYS_2026_FROM_1125 = {"2026-12-25"}


def _calendar_cache_path(year: int) -> str:
    return os.path.join(DATA_DIR, f"trading_calendar_{year}.json")


def fetch_and_cache_holiday_schedule(fetch_json_fn) -> Optional[int]:
    """
    Call the TWSE holidaySchedule OpenAPI (via `fetch_json_fn`, a callable
    taking a URL and returning parsed JSON or None — injected so this
    module doesn't need its own `requests` dependency/network mocking) and
    cache whichever year it returns to data/trading_calendar_<year>.json.

    Returns the year that was cached, or None if the fetch failed.
    """
    url = "https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule"
    rows = fetch_json_fn(url)
    if not rows:
        return None

    # Confirmed live shape (2026-11-25): rows like
    # {"Name": "...", "Date": "1160101", "Weekday": "五", "Description": "..."}
    # — "Date" is a compact "YYYMMDD" ROC-year string with no separators.
    # Still detected dynamically (not hardcoded to "Date") in case the API
    # changes, and both delimited and compact formats are handled below.
    sample = rows[0] if isinstance(rows, list) and rows else {}
    date_key = next((k for k in sample.keys() if "date" in k.lower() or "日期" in k), None)
    if date_key is None:
        return None

    holidays = set()
    year = None
    for row in rows:
        raw_date = str(row.get(date_key) or "").strip()
        if not raw_date:
            continue
        if "/" in raw_date or "-" in raw_date:
            # Delimited "YYY/MM/DD" (ROC) or "YYYY/MM/DD" (AD).
            parts = raw_date.replace("-", "/").split("/")
            if len(parts) != 3:
                continue
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        elif len(raw_date) == 7:
            # Confirmed live shape (2026-11-25): compact "YYYMMDD", ROC year
            # with no separators, e.g. "1160101" = 民國116年01月01日.
            y, m, d = int(raw_date[0:3]), int(raw_date[3:5]), int(raw_date[5:7])
        elif len(raw_date) == 8:
            # Same compact shape but an AD year (4 digits) instead of ROC.
            y, m, d = int(raw_date[0:4]), int(raw_date[4:6]), int(raw_date[6:8])
        else:
            continue
        if y < 1911:
            y += 1911  # ROC year -> AD year
        iso = f"{y:04d}-{m:02d}-{d:02d}"
        holidays.add(iso)
        year = y

    if year is None:
        return None

    with open(_calendar_cache_path(year), 'w', encoding='utf-8') as f:
        json.dump({
            "year": year,
            "fetched_at": datetime.now().astimezone().isoformat(),
            "source": "https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule",
            "holidays": sorted(holidays),
        }, f, indent=2, ensure_ascii=False)
    return year


def _load_cached_holidays(year: int) -> Optional[Set[str]]:
    path = _calendar_cache_path(year)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return set(json.load(f).get("holidays", []))
    except Exception:
        return None


def is_trading_day(date: datetime) -> bool:
    """
    True if `date` is a trading day: not a weekend, and not a known
    holiday for a year we have a cached calendar for. For 2026 specifically,
    also checks the confirmed-from-2026-11-25 holiday set even without a
    cache file (see module docstring).

    For years with no cached calendar and no confirmed override, this is
    "weekday = trading day" only — it CANNOT know about ad hoc holidays,
    and callers needing certainty for a specific past date should
    cross-check against an actual data source instead (see module
    docstring, point 3).
    """
    if date.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    iso = date.strftime("%Y-%m-%d")
    if date.year == 2026 and iso in _CONFIRMED_HOLIDAYS_2026_FROM_1125:
        return False
    cached = _load_cached_holidays(date.year)
    if cached and iso in cached:
        return False
    return True


def most_recent_trading_day(from_date: Optional[datetime] = None, max_lookback_days: int = 14) -> datetime:
    """Walk backward from `from_date` (default: now) to the most recent trading day (inclusive)."""
    day = from_date or datetime.now()
    for _ in range(max_lookback_days):
        if is_trading_day(day):
            return day
        day -= timedelta(days=1)
    raise RuntimeError(f"No trading day found within {max_lookback_days} days of {from_date}")
