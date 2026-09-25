"""Product data and validation, independent of Flask and presentation."""

from dataclasses import dataclass, field
import math


def validate_number(label, value, minimum, maximum):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")


@dataclass(frozen=True)
class Basin:
    id: str
    name: str
    south: float
    north: float
    west: float
    east: float

    def __post_init__(self):
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Basin ID and name are required.")
        validate_number("Southern bound", self.south, -90, 90)
        validate_number("Northern bound", self.north, -90, 90)
        validate_number("Western bound", self.west, -180, 180)
        validate_number("Eastern bound", self.east, -180, 180)
        if self.south >= self.north or self.west >= self.east:
            raise ValueError("Basin bounds must be ordered south to north and west to east.")

    def contains(self, disturbance):
        return (
            self.south <= disturbance.latitude <= self.north
            and self.west <= disturbance.longitude <= self.east
        )


@dataclass(frozen=True)
class Disturbance:
    name: str
    latitude: float
    longitude: float
    description: str
    probability_48h: int
    probability_7d: int

    def __post_init__(self):
        if not self.name.strip() or not self.description.strip():
            raise ValueError("A name and description are required.")
        validate_number("Latitude", self.latitude, -90, 90)
        validate_number("Longitude", self.longitude, -180, 180)
        for label, value in (
            ("48-hour formation probability", self.probability_48h),
            ("7-day formation probability", self.probability_7d),
        ):
            validate_number(label, value, 0, 100)
            if not isinstance(value, int):
                raise ValueError(f"{label} must be a whole percentage.")


@dataclass
class Outlook:
    basin: Basin
    disturbances: list[Disturbance] = field(default_factory=list)

    def __post_init__(self):
        self.disturbances = list(self.disturbances)
        for disturbance in self.disturbances:
            self._validate_location(disturbance)

    def _validate_location(self, disturbance):
        if not self.basin.contains(disturbance):
            raise ValueError(f"Disturbance must be within {self.basin.name} basin bounds.")

    def add_disturbance(self, disturbance):
        self._validate_location(disturbance)
        self.disturbances.append(disturbance)
