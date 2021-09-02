import os
import random
import typing

from airports_bot.airport import Airport, AirportType
from airports_bot.airportstable import AirportsTable
from airports_bot.download import download
from airports_bot.runwaystable import RunwaysTable

class DB:
    def __init__(self) -> None:
        self._airports: typing.Dict[str, Airport] = {}
        self._large: typing.List[str] = []
        self._medium: typing.List[str] = []
        self._small: typing.List[str] = []
        self._other: typing.List[str] = []

    def load(self, cache_dir: str, reset_cache: bool) -> None:
        airports_csv = os.path.join(cache_dir, "airports.csv")
        runways_csv = os.path.join(cache_dir, "runways.csv")
        if reset_cache:
            for file_name in [airports_csv, runways_csv]:
                if os.path.exists(file_name):
                    os.remove(file_name)
        airports = AirportsTable(download("https://ourairports.com/data/airports.csv", airports_csv))
        runways = RunwaysTable(download("https://ourairports.com/data/runways.csv", runways_csv))
        airports.compute_bounds(runways.to_dict())
        airports.check()
        for airport in airports.good_airports():
            self._airports[airport.icao_code()] = airport

    def get(self, icao: str) -> typing.Optional[Airport]:
        icao = icao.strip().upper()
        for airport in self._airports.values():
            if airport.matches_code(icao):
                return airport
        return None

    def get_random(self) -> Airport:
        if len(self._large) > 0 and random.choice([True, False]):
            return self._airports[random.choice(self._large)]
        if len(self._medium) > 0 and random.choice([True, False]):
            return self._airports[random.choice(self._medium)]
        if len(self._small) > 0 and random.choice([True, False]):
            return self._airports[random.choice(self._small)]
        return self._airports[random.choice(list(self._airports.keys()))]
