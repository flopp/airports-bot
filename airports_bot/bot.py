import configparser
import math
import os
import typing

import appdirs  # type: ignore
from s2sphere import Angle, LatLngRect  # type: ignore
import staticmaps  # type: ignore
import tweepy  # type: ignore

from airports_bot.db import DB
from airports_bot.airport import Airport
from airports_bot.version import __user_agent__

class Bot:
    def __init__(self, config_file_name: str) -> None:
        self._db = DB()
        self._cache_dir = os.path.join(appdirs.user_cache_dir("flopp.airports-bot"))

        self._config = configparser.ConfigParser()
        self._config.read(config_file_name)
        if "default" in self._config:
            if "CACHE_DIR" in self._config["default"]:
                self._cache_dir = self._config["default"]["CACHE_DIR"]
        self._last = []
        self._lastFileName = os.path.join(self._cache_dir, "last.txt")
        if os.path.isfile(self._lastFileName):
            with open(self._lastFileName) as f:
                for line in f:
                    self._last.append(line.strip())

    def load_data(self, reset: bool) -> None:
        self._db.load(self._cache_dir, reset)

    def get_airport(self, code: str) -> typing.Optional[Airport]:
        return self._db.get(code)

    def get_random_airport(self) -> Airport:
        airport = self._db.get_random(self._last)
        self._last.append(airport.icao_code())
        if len(self._last) >= self._db.count() // 2:
            self._last.pop(0)
        with open(self._lastFileName, "w") as f:
            f.write("\n".join(self._last))
        return airport

    def create_image(self, airport: Airport) -> str:
        width = 640
        height = 640
        bounds = airport.bounds()
        assert bounds
        center = bounds.get_center()
        zoom = Bot.get_bounds_zoom(bounds, width, height)
        tiles = staticmaps.tile_provider_ArcGISWorldImagery
        downloader = staticmaps.TileDownloader()
        downloader.set_user_agent(__user_agent__)
        context = staticmaps.Context()
        context.set_zoom(zoom)
        context.set_center(center)
        context.set_tile_provider(tiles)
        context.set_tile_downloader(downloader)
        context.set_cache_dir(os.path.join(self._cache_dir, "tiles"))
        image = context.render_cairo(width, height)
        image_file = os.path.join(self._cache_dir, f"{airport.icao_code()}-{width}x{height}.png")
        image.write_to_png(image_file)
        return image_file

    def prepare_tweet(self, airport: Airport) -> typing.Tuple[str, str]:
        image_file = self.create_image(airport)
        tags = [f"#{airport.icao_code()}"]
        if airport.iata_code() != "":
            tags.append(f"#{airport.iata_code()}")
        if airport.twitter() != "":
            tags.append(airport.twitter())
        if airport.city() != "":
            tags.append(f"#{''.join(airport.city().split())}")
        tags.append("#airport")
        tags.append("#randomairport")
        tags.append("#aviation")
        tags.append("#avgeek")
        tags.append("#avgeeks")
        return (
            image_file,
            f"{airport.fancy_name()}, {airport.location()}\n"
            + f"https://airports.flopp.net/a/{airport.icao_code()}\n"
            + " ".join(tags),
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
        rad_x2 = math.log((1 + sin) / (1 - sin)) / 2
        return max(min(rad_x2, math.pi), -math.pi) / 2

    @staticmethod
    def _zoom(size: int, fraction: float) -> int:
        return math.floor(math.log(size / 256.0 / fraction) / math.log(2))

    @staticmethod
    def get_bounds_zoom(bounds: LatLngRect, width: int, height: int) -> int:
        max_zoom = 21
        lat_fraction = (Bot._lat_rad(bounds.lat_hi()) - Bot._lat_rad(bounds.lat_lo())) / math.pi
        lng_diff = bounds.lng_hi().degrees - bounds.lng_lo().degrees
        lng_fraction = (lng_diff if lng_diff >= 0 else (lng_diff + 360)) / 360.0
        lat_zoom = Bot._zoom(height, lat_fraction)
        lng_zoom = Bot._zoom(width, lng_fraction)
        return min(max_zoom, min(lat_zoom, lng_zoom))
