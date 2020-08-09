import configparser
import math
import os
import typing

import appdirs  # type: ignore
from s2sphere import Angle, LatLng, LatLngRect
import tweepy

from airports_bot.db import DB
from airports_bot.airport import Airport
from airports_bot.download import download


class Bot:
    def __init__(self, config_file_name: str) -> None:
        self._db = DB()
        self._cache_dir = os.path.join(appdirs.user_cache_dir("flopp.airports-bot"))

        self._config = configparser.ConfigParser()
        self._config.read(config_file_name)
        if "default" in self._config:
            if "CACHE_DIR" in self._config["default"]:
                self._cache_dir = self._config["default"]["CACHE_DIR"]

    def load_data(self, reset: bool) -> None:
        self._db.load(self._cache_dir, reset)

    def get_airport(self, code: str) -> typing.Optional[Airport]:
        return self._db.get(code)

    def get_random_airport(self) -> Airport:
        return self._db.get_random()

    def create_image(self, airport: Airport) -> str:
        width = 640
        height = 640
        assert airport._bounds
        center = airport._bounds.get_center()
        zoom = self.get_bounds_zoom(airport._bounds, width, height)
        url = f"https://maps.googleapis.com/maps/api/staticmap?center={center.lat().degrees},{center.lng().degrees}&zoom={zoom}&size={width}x{height}&maptype=satellite&key={self._config['GOOGLE']['API_KEY']}"
        image_file = os.path.join(self._cache_dir, f"{airport.icao_code()}-{width}x{height}.png")
        download(url, image_file)
        return image_file

    def prepare_tweet(self, airport: Airport) -> typing.Tuple[str, str]:
        image_file = self.create_image(airport)
        tags = [f"#{airport.icao_code()}"]
        if airport._iata_code != "":
            tags.append(f"#{airport._iata_code}")
        tags.append("#airport")
        tags.append("#randomairport")
        return (
            image_file,
            f"{airport.fancy_name()}, {airport._location}\nhttps://airports.flopp.net/a/{airport.icao_code()}\n{' '.join(tags)}",
        )

    def tweet(self, image_file: str, text: str) -> None:
        auth = tweepy.OAuthHandler(self._config["TWITTER"]["API_KEY"], self._config["TWITTER"]["API_SECRET_KEY"])
        auth.set_access_token(self._config["TWITTER"]["ACCESS_TOKEN"], self._config["TWITTER"]["ACCESS_TOKEN_SECRET"])
        api = tweepy.API(auth)
        api.verify_credentials()
        api.update_with_media(image_file, status=text)

    @staticmethod
    def _lat_rad(lat: Angle) -> float:
        sin = math.sin(lat.radians)
        radX2 = math.log((1 + sin) / (1 - sin)) / 2
        return max(min(radX2, math.pi), -math.pi) / 2

    @staticmethod
    def _zoom(size: int, fraction: float) -> int:
        return math.floor(math.log(size / 256.0 / fraction) / math.log(2))

    def get_bounds_zoom(self, bounds: LatLngRect, width: int, height: int) -> int:
        world_width = 256
        world_height = 256
        max_zoom = 21
        lat_fraction = (Bot._lat_rad(bounds.lat_hi()) - Bot._lat_rad(bounds.lat_lo())) / math.pi
        lng_diff = bounds.lng_hi().degrees - bounds.lng_lo().degrees
        lng_fraction = (lng_diff if lng_diff >= 0 else (lng_diff + 360)) / 360.0
        lat_zoom = Bot._zoom(height, lat_fraction)
        lng_zoom = Bot._zoom(width, lng_fraction)
        return min(max_zoom, min(lat_zoom, lng_zoom))
