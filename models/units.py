from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


class UnitCategory:
    """Tillåtna kategorier för köksmått."""

    WEIGHT = "weight"
    VOLUME = "volume"
    COUNT = "count"
    SPOON = "spoon"
    OTHER = "other"


@dataclass(frozen=True)
class Unit:
    code: str
    name: str
    plural: str
    category: str
    summable: bool

    def to_dict(self) -> Dict[str, str | bool]:
        """Enkel serialisering till JSON-vänlig dict."""
        return asdict(self)


# Basuppsättning av svenska, metriska och köksnära enheter.
_UNITS: List[Unit] = [
    # Vikt
    Unit("g", "gram", "gram", UnitCategory.WEIGHT, True),
    Unit("kg", "kilogram", "kilogram", UnitCategory.WEIGHT, True),
    # Volym
    Unit("ml", "milliliter", "milliliter", UnitCategory.VOLUME, True),
    Unit("cl", "centiliter", "centiliter", UnitCategory.VOLUME, True),
    Unit("dl", "deciliter", "deciliter", UnitCategory.VOLUME, True),
    Unit("l", "liter", "liter", UnitCategory.VOLUME, True),
    # Köksmått (skedmått är volym men separata för UX)
    Unit("krm", "kryddmått", "kryddmått", UnitCategory.SPOON, True),
    Unit("tsk", "tesked", "teskedar", UnitCategory.SPOON, True),
    Unit("msk", "matsked", "matskedar", UnitCategory.SPOON, True),
    # Styck
    Unit("st", "styck", "stycken", UnitCategory.COUNT, True),
    # Övrigt – ej summerbara, textuella mått
    Unit("nypa", "nypa", "nypor", UnitCategory.OTHER, False),
    Unit("knippe", "knippe", "knippen", UnitCategory.OTHER, False),
    Unit("efter_smak", "efter smak", "efter smak", UnitCategory.OTHER, False),
]

_UNITS_BY_CODE: Dict[str, Unit] = {unit.code: unit for unit in _UNITS}


def get_all_units() -> List[Unit]:
    """Returnera alla enheter i definierad ordning."""
    return list(_UNITS)


def get_units_by_category(category: str) -> List[Unit]:
    """Filtrera enheter per kategori (ex. UnitCategory.WEIGHT)."""
    return [u for u in _UNITS if u.category == category]


def get_unit(code: str) -> Optional[Unit]:
    """Hämta en enhet på kod, eller None om den inte finns."""
    return _UNITS_BY_CODE.get(code)


def is_summable(code: str) -> bool:
    """Returnera True om enheten kan summeras i t.ex. inköpslista."""
    unit = get_unit(code)
    return bool(unit and unit.summable)


__all__ = [
    "Unit",
    "UnitCategory",
    "get_all_units",
    "get_units_by_category",
    "get_unit",
    "is_summable",
]
