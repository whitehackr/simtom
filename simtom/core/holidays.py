"""Generic holiday calculation utilities - industry agnostic.

Provides date calculations for major holidays and shopping periods
without making assumptions about their business impact.
"""

from datetime import date, timedelta
from typing import Dict, List, Set
import calendar


def get_major_holidays(year: int) -> Dict[str, date]:
    """Get major holidays for a given year.

    Returns dictionary mapping holiday names to dates.
    No assumptions about business impact - just date calculations.
    """
    holidays = {}

    # Fixed date holidays
    holidays['new_years_day'] = date(year, 1, 1)
    holidays['valentines_day'] = date(year, 2, 14)
    holidays['independence_day'] = date(year, 7, 4)
    holidays['halloween'] = date(year, 10, 31)
    holidays['christmas_eve'] = date(year, 12, 24)
    holidays['christmas_day'] = date(year, 12, 25)
    holidays['new_years_eve'] = date(year, 12, 31)

    # Calculated holidays
    holidays['mothers_day'] = _get_nth_weekday(year, 5, 0, 2)  # 2nd Sunday in May
    holidays['fathers_day'] = _get_nth_weekday(year, 6, 0, 3)  # 3rd Sunday in June
    holidays['labor_day'] = _get_nth_weekday(year, 9, 0, 1)   # 1st Monday in September

    # Thanksgiving and related shopping days
    thanksgiving = _get_nth_weekday(year, 11, 3, 4)  # 4th Thursday in November
    holidays['thanksgiving'] = thanksgiving
    holidays['black_friday'] = thanksgiving + timedelta(days=1)
    holidays['cyber_monday'] = thanksgiving + timedelta(days=4)

    return holidays


def get_holiday_periods(year: int) -> Dict[str, tuple]:
    """Get extended holiday periods (start_date, end_date).

    These represent multi-day periods often associated with
    specific business patterns across industries.
    """
    holidays = get_major_holidays(year)

    periods = {
        # Back-to-school season
        'back_to_school': (date(year, 8, 15), date(year, 9, 15)),

        # Black Friday week (Wed before through Cyber Monday)
        'black_friday_week': (
            holidays['thanksgiving'] - timedelta(days=1),
            holidays['cyber_monday']
        ),

        # Christmas shopping season
        'christmas_shopping': (date(year, 12, 1), date(year, 12, 23)),

        # Post-Christmas period
        'post_christmas': (date(year, 12, 26), date(year + 1, 1, 2)),

        # Valentine's week
        'valentines_week': (
            holidays['valentines_day'] - timedelta(days=3),
            holidays['valentines_day'] + timedelta(days=1)
        ),

        # Mother's Day week
        'mothers_day_week': (
            holidays['mothers_day'] - timedelta(days=3),
            holidays['mothers_day'] + timedelta(days=1)
        ),

        # Summer holiday season
        'summer_holidays': (date(year, 6, 15), date(year, 8, 15)),

        # Year-end holidays
        'year_end_holidays': (date(year, 12, 20), date(year + 1, 1, 5)),
    }

    return periods


def is_holiday(target_date: date, holiday_name: str) -> bool:
    """Check if a date matches a specific holiday."""
    year = target_date.year
    holidays = get_major_holidays(year)
    return holidays.get(holiday_name) == target_date


def is_holiday_period(target_date: date, period_name: str) -> bool:
    """Check if a date falls within a holiday period."""
    year = target_date.year
    periods = get_holiday_periods(year)

    if period_name not in periods:
        return False

    start_date, end_date = periods[period_name]
    return start_date <= target_date <= end_date


def get_active_holidays(target_date: date) -> List[str]:
    """Get list of all holidays that apply to a specific date.

    Returns both exact holiday matches and holiday periods.
    """
    active = []
    year = target_date.year

    # Check exact holidays
    holidays = get_major_holidays(year)
    for holiday_name, holiday_date in holidays.items():
        if target_date == holiday_date:
            active.append(holiday_name)

    # Check holiday periods
    periods = get_holiday_periods(year)
    for period_name, (start_date, end_date) in periods.items():
        if start_date <= target_date <= end_date:
            active.append(period_name)

    return active


def is_weekend(target_date: date) -> bool:
    """Check if date falls on weekend (Saturday=5, Sunday=6)."""
    return target_date.weekday() >= 5


def get_dates_in_range(start_date: date, end_date: date) -> List[date]:
    """Get list of all dates in range (inclusive)."""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def _get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Get the nth occurrence of a weekday in a month.

    Args:
        year: Year
        month: Month (1-12)
        weekday: Day of week (0=Monday, 6=Sunday)
        n: Which occurrence (1=first, 2=second, etc.)
    """
    # Find first day of month
    first_day = date(year, month, 1)

    # Find first occurrence of target weekday
    days_until_weekday = (weekday - first_day.weekday()) % 7
    first_occurrence = first_day + timedelta(days=days_until_weekday)

    # Add weeks to get nth occurrence
    target_date = first_occurrence + timedelta(weeks=n-1)

    # Make sure we didn't go into next month
    if target_date.month != month:
        # Handle case where nth occurrence doesn't exist (e.g., 5th Monday)
        # Fall back to last occurrence
        target_date = first_occurrence + timedelta(weeks=n-2)

    return target_date