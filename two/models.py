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
class FormationArea:
    """Rectangular or elliptical area within geographic bounds."""

    south: float
    north: float
    west: float
    east: float
    shape: str = "rectangle"

    def __post_init__(self):
        if self.shape not in ("rectangle", "ellipse"):
            raise ValueError("Area shape must be rectangle or ellipse.")
        validate_number("Area southern bound", self.south, -90, 90)
        validate_number("Area northern bound", self.north, -90, 90)
        validate_number("Area western bound", self.west, -180, 180)
        validate_number("Area eastern bound", self.east, -180, 180)
        if self.south >= self.north or self.west >= self.east:
            raise ValueError("Area bounds must be ordered south to north and west to east.")

    def contains(self, latitude, longitude):
        if not (self.south <= latitude <= self.north and self.west <= longitude <= self.east):
            return False
        if self.shape == "ellipse":
            lat, lon = self.center
            distance = ((latitude - lat) / ((self.north - self.south) / 2)) ** 2
            distance += ((longitude - lon) / ((self.east - self.west) / 2)) ** 2
            return distance <= 1 + 1e-12
        return True

    @property
    def center(self):
        return ((self.south + self.north) / 2, (self.west + self.east) / 2)


MARKING_TYPES = {
    "area_only": "Area of interest (no X)",
    "x_to_area": "X moving into an area (arrow)",
    "x_in_area": "X within an area",
}


@dataclass(frozen=True)
class Disturbance:
    name: str
    latitude: float | None
    longitude: float | None
    description: str
    probability_48h: int
    probability_7d: int
    marking_type: str
    area: FormationArea

    def __post_init__(self):
        if (not isinstance(self.name, str) or not self.name.strip()
                or not isinstance(self.description, str) or not self.description.strip()):
            raise ValueError("A name and description are required.")
        if not isinstance(self.marking_type, str) or self.marking_type not in MARKING_TYPES:
            raise ValueError("Select a valid marking type.")
        if not isinstance(self.area, FormationArea):
            raise ValueError("A formation area is required.")
        if self.marking_type == "area_only":
            if self.latitude is not None or self.longitude is not None:
                raise ValueError("An area-only disturbance must not have X coordinates.")
        else:
            validate_number("X latitude", self.latitude, -90, 90)
            validate_number("X longitude", self.longitude, -180, 180)
            inside = self.area.contains(self.latitude, self.longitude)
            if self.marking_type == "x_in_area" and not inside:
                raise ValueError("The X must be within the formation area.")
            if self.marking_type == "x_to_area" and inside:
                raise ValueError("The X must be outside the formation area when using an arrow.")
        for label, value in (
            ("48-hour formation probability", self.probability_48h),
            ("7-day formation probability", self.probability_7d),
        ):
            validate_number(label, value, 0, 100)
            if not isinstance(value, int):
                raise ValueError(f"{label} must be a whole percentage.")

    @classmethod
    def from_dict(cls, data):
        values = dict(data)
        area = values.get("area")
        if not isinstance(area, dict):
            raise ValueError("Provide formation area bounds.")
        values["area"] = FormationArea(**area)
        values.setdefault("latitude", None)
        values.setdefault("longitude", None)
        return cls(**values)

    @property
    def arrow(self):
        """Arrow endpoints are derived, so they cannot drift from the X/area."""
        if self.marking_type == "x_to_area":
            return ((self.latitude, self.longitude), self.area.center)
        return None


@dataclass
class Outlook:
    basin: Basin
    disturbances: list[Disturbance] = field(default_factory=list)

    def __post_init__(self):
        self.disturbances = list(self.disturbances)
        for disturbance in self.disturbances:
            self._validate_location(disturbance)

    def _validate_location(self, disturbance):
        if disturbance.latitude is not None and not self.basin.contains(disturbance):
            raise ValueError(f"Disturbance must be within {self.basin.name} basin bounds.")
        area = disturbance.area
        if not (self.basin.south <= area.south < area.north <= self.basin.north
                and self.basin.west <= area.west < area.east <= self.basin.east):
            raise ValueError(f"Formation area must be within {self.basin.name} basin bounds.")

    def add_disturbance(self, disturbance):
        self._validate_location(disturbance)
        self.disturbances.append(disturbance)
