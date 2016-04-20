import pandas as pd
import pytest

from star.models import LightAwareDatetime, Location


@pytest.mark.parametrize("datetime,is_light", [
    ("2016-01-01 06:56", False),
    ("2016-01-01 06:58", False),
    ("2016-01-01 07:25", False),
    ("2016-01-01 07:27", True),
    ("2016-01-01 17:11", True),
    ("2016-01-01 17:13", False),
    ("2016-01-01 17:39", False),
    ("2016-01-01 17:41", False),
])
def test_is_light(location, datetime, is_light):
    datetime = LightAwareDatetime(pd.to_datetime(datetime),
                                  Location(**location))
    assert datetime.is_light() == is_light


@pytest.mark.parametrize("datetime,is_twilight", [
    ("2016-01-01 06:56", False),
    ("2016-01-01 06:58", True),
    ("2016-01-01 07:25", True),
    ("2016-01-01 07:27", False),
    ("2016-01-01 17:11", False),
    ("2016-01-01 17:13", True),
    ("2016-01-01 17:39", True),
    ("2016-01-01 17:41", False),
])
def test_is_twilight(location, datetime, is_twilight):
    datetime = LightAwareDatetime(pd.to_datetime(datetime),
                                  Location(**location))
    assert datetime.is_twilight() == is_twilight


@pytest.mark.parametrize("datetime,is_dark", [
    ("2016-01-01 06:56", True),
    ("2016-01-01 06:58", False),
    ("2016-01-01 07:25", False),
    ("2016-01-01 07:27", False),
    ("2016-01-01 17:11", False),
    ("2016-01-01 17:13", False),
    ("2016-01-01 17:39", False),
    ("2016-01-01 17:41", True),
])
def test_is_light(location, datetime, is_dark):
    datetime = LightAwareDatetime(pd.to_datetime(datetime),
                                  Location(**location))
    assert datetime.is_dark() == is_dark
