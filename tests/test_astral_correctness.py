import datetime

import pytest

from star.models import Location


def round_datetime(dt, dateDelta=datetime.timedelta(minutes=1)):
    """Round a datetime object to a multiple of a timedelta
    dt : datetime.datetime object, default now.
    dateDelta : timedelta object, we round to a multiple of this, default 1
    minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
            Stijn Nevens 2014 - Changed to use only datetime objects as
            variables
    """
    roundTo = dateDelta.total_seconds()

    seconds = dt.timestamp()
    # // is a floor division, not a comment on following line:
    rounding = (seconds + roundTo / 2) // roundTo * roundTo
    return dt + datetime.timedelta(0, rounding - seconds, -dt.microsecond)


@pytest.mark.parametrize("sunset", [
    [2016, 2, 16, 17, 58],
    [2015, 6, 16, 20, 34]
])
def test_astral_sunset_correctness(location, sunset):
    location = Location(**location)
    date = datetime.date(*sunset[:3])
    calculated_sunset = round_datetime(location.sunset(date))

    assert calculated_sunset == datetime.datetime(*sunset,
                                                  tzinfo=calculated_sunset.tzinfo)


@pytest.mark.parametrize("dusk", [
    [2016, 2, 16, 18, 24],
    [2015, 6, 16, 21, 4]
])
def test_astral_dusk_correctness(location, dusk):
    location = Location(**location)
    date = datetime.date(*dusk[:3])
    calculated_dusk = round_datetime(location.dusk(date))

    assert calculated_dusk == datetime.datetime(*dusk,
                                                tzinfo=calculated_dusk.tzinfo)
