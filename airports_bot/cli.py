#!/usr/bin/env python3

import logging
import typing

import click

from airports_bot.bot import Bot


@click.command()
@click.argument("airport_code", nargs=-1, type=str)
@click.option("-c", "--config", default="config.py", type=click.Path(exists=True))
@click.option("-r", "--reset", is_flag=True)
@click.option("-t", "--tweet", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
def main(airport_code: typing.List[str], config: str, reset: bool, tweet: bool, verbose: bool,) -> None:
    if verbose:
        logging.basicConfig(level=logging.INFO)
    bot = Bot(config)
    bot.load_data(reset)
    airports = []
    if len(airport_code) > 0:
        for code in airport_code:
            airport = bot.get_airport(code)
            if airport is None:
                logging.warn("Cannot find airport matching '%s'", airport_code)
                continue
            airports.append(airport)
    else:
        airports.append(bot.get_random_airport())
    for airport in airports:
        logging.info("=> %s", airport.fancy_name())
        image_file, text = bot.prepare_tweet(airport)
        if tweet:
            bot.tweet(image_file, text)


if __name__ == "__main__":
    main()
