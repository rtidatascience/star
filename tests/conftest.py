import os

import pandas as pd
import pytest

from star import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def location():
    return {
        "name": "Durham",
        "region": "NC, USA",
        "latitude": 35.9940329,
        "longitude": -78.898619,
        "timezone": 'America/New_York',
        "elevation": 120,
    }


@pytest.fixture
def data():
    dir = os.path.dirname(__file__)
    path = os.path.join(dir, "sample_data/datetime-race-gender-make.csv")
    data = pd.read_csv(path, parse_dates=['datetime'])
    return data
