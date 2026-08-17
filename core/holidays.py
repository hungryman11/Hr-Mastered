"""Nigeria public-holiday calendar used for leave-day calculations.

Movable Islamic dates are government declarations; confirmed 2026 dates are
included below and HR can add future declarations through /api/holidays/.
"""
from datetime import date, timedelta


CONFIRMED_NIGERIAN_MOVABLE_HOLIDAYS = {
    2026: {
        date(2026, 3, 19), date(2026, 3, 20),  # Eid-ul-Fitr
        date(2026, 5, 27), date(2026, 5, 28),  # Eid-ul-Adha
        date(2026, 8, 26),  # Eid-el-Maulud (subject to official declaration)
    },
}


def _easter_sunday(year):
    """Gregorian computus, sufficient for Nigerian Good Friday/Easter Monday."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def nigerian_public_holidays(start_year, end_year):
    holidays = set()
    for year in range(start_year, end_year + 1):
        easter = _easter_sunday(year)
        holidays.update({
            date(year, 1, 1),       # New Year
            easter - timedelta(days=2),  # Good Friday
            easter + timedelta(days=1),  # Easter Monday
            date(year, 5, 1),       # Workers' Day
            date(year, 6, 12),      # Democracy Day
            date(year, 10, 1),      # Independence Day
            date(year, 12, 25),     # Christmas
            date(year, 12, 26),     # Boxing Day
        })
        holidays.update(CONFIRMED_NIGERIAN_MOVABLE_HOLIDAYS.get(year, set()))
    return holidays
