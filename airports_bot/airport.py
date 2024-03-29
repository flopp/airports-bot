import enum
import logging
import typing

import pycountry  # type: ignore
from s2sphere import LatLng, LatLngRect  # type: ignore

from airports_bot.runway import Runway


class AirportType(enum.Enum):
    UNKNOWN = "unknown"
    LARGE_AIRPORT = "large_airport"
    MEDIUM_AIRPORT = "medium_airport"
    SMALL_AIRPORT = "small_airport"
    SEAPLANE_BASE = "seaplane_base"
    BALLOONPORT = "balloonport"
    HELIPORT = "heliport"
    CLOSED = "closed"


def short_airport_type(t: AirportType) -> str:
    return {
        AirportType.UNKNOWN: "?",
        AirportType.LARGE_AIRPORT: "L",
        AirportType.MEDIUM_AIRPORT: "M",
        AirportType.SMALL_AIRPORT: "S",
        AirportType.SEAPLANE_BASE: "W",
        AirportType.BALLOONPORT: "B",
        AirportType.HELIPORT: "H",
        AirportType.CLOSED: "C",
    }.get(t, "?")


class Airport:
    def __init__(self) -> None:
        self._icao_code = ""
        self._iata_code = ""
        self._type: AirportType = AirportType.UNKNOWN
        self._name = ""

        self._latlng: typing.Optional[LatLng] = None
        self._bounds: typing.Optional[LatLngRect] = None
        self._city = ""
        self._location = ""
        self._twitter = ""

    def set_from_array(self, array: typing.List[typing.Any]) -> None:
        if len(array) != 18:
            raise IndexError(f"expecting 18 items. received '{', '.join(array)}' ({len(array)} items)")

        # self._id = array[0]
        self._icao_code = array[1].strip().upper()
        airport_type = array[2]
        self._name = array[3]
        latitude_deg = array[4].replace(",", ".")
        longitude_deg = array[5].replace(",", ".")
        # self._elevation_ft = array[6]
        # self._continent = array[7]
        iso_country = array[8]
        # self._iso_region = array[9]
        self._city = array[10]
        # self._scheduled_service = array[11]
        # self._gps_code = array[12]
        self._iata_code = array[13].strip().upper()
        # self._local_code = array[14]
        # self._home_link = array[15]
        # self._wikipedia_link = array[16]
        # self._keywords = array[17]

        if self._iata_code == self._icao_code:
            self._iata_code = ""
        for valid_airport_type in AirportType:
            if valid_airport_type.value == airport_type:
                self._type = valid_airport_type
                break
        else:
            logging.warning("%s: unknown airport type: %s", self._icao_code, airport_type)
        self._latlng = LatLng.from_degrees(float(latitude_deg), float(longitude_deg))
        self._bounds = LatLngRect.from_point(self._latlng)
        self._location = Airport.fancy_location(iso_country, self._city)

    def icao_code(self) -> str:
        return self._icao_code

    def iata_code(self) -> str:
        return self._iata_code

    def matches_code(self, needle: str) -> bool:
        return needle == self._icao_code or needle == self._iata_code

    def fancy_name(self) -> str:
        code = self._icao_code
        if self._iata_code != "":
            code = f"{code}/{self._iata_code}"
        return f"{code} - {self._name}"

    def bounds(self) -> typing.Optional[LatLngRect]:
        return self._bounds

    def city(self) -> str:
        return self._city

    def location(self) -> str:
        return self._location
    
    def twitter(self) -> str:
        return self._twitter
    
    def set_twitter(self, s: str) -> None:
        self._twitter = s

    @staticmethod
    def fancy_location(iso_country: str, city: str) -> str:
        country = None
        if iso_country in ["KS", "XK"]:
            country = "Kosovo"
        elif iso_country in ["ZZ"]:
            country = None
        else:
            country = pycountry.countries.get(alpha_2=iso_country).name

        if country is None or country == "":
            if city is None or city == "":
                return "Unknown Location"
            return city
        if city is None or city == "":
            return f"Somewhere in {country}"
        return f"{city}, {country}"

    def airport_type(self) -> AirportType:
        return self._type

    def empty_bounds(self) -> bool:
        assert self._bounds is not None
        return self._bounds.is_point()

    def excessive_bounds(self) -> bool:
        assert self._bounds is not None
        return self._bounds.lat().get_length() > 0.01 or self._bounds.lng().get_length() > 0.01

    def compute_bounds(self, runways: typing.List[Runway]) -> None:
        assert self._bounds is not None
        for runway in runways:
            if runway.has_hard_surface():
                self._bounds = self._bounds.union(runway.bounds())
