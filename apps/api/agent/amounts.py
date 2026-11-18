"""Amount parsing in plain code: a small language model converts « 2 M€ » unreliably."""

import re

UNITS = (
    r"M\s?€|M\s?euros?|millions?(?:\s+d['’]\s?euros?)?|"
    r"k\s?€|k\s?euros?|milliers?(?:\s+d['’]\s?euros?)?|€|euros?"
)
PATTERN = re.compile(rf"(\d[\d   ]*(?:[.,]\d+)?)\s*({UNITS})", re.IGNORECASE)


def multiplier(unit: str) -> int:
    unit = unit.lower()
    if unit.startswith(("millier", "k")):
        return 1_000
    if unit.startswith("m"):  # M€, M euros, millions (« milliers » was handled above)
        return 1_000_000
    return 1


def parse_amount(text: str) -> float | None:
    """First amount in euros in the text: « 2 M€ », « 2,5 millions d'euros », « 350 000 € »."""
    for match in PATTERN.finditer(text):
        number = re.sub(r"[\s  ]", "", match.group(1)).replace(",", ".")
        try:
            return float(number) * multiplier(match.group(2))
        except ValueError:
            continue
    return None
