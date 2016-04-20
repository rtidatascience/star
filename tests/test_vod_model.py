import datetime
import os

import pandas as pd

from star.models import VODModel
import numpy as np

def model_factory(data, **kwargs):
    location = kwargs['location']
    columns = kwargs.get('columns', {"target_column": "race",
                                     "datetime_column": 'datetime'})
    options = kwargs.get("options", {"target_group": 1})
    return VODModel(data, location=location, columns=columns, options=options)

def test_date_time_formats():
    dir = os.path.dirname(__file__)
    path = os.path.join(dir, "sample_data/date-time-examples.csv")
    data = pd.read_csv(path, parse_dates={"datetime": ['date', 'time']})

    assert data['datetime'].dtype == np.dtype('datetime64[ns]')



def test_minimum_variables_exist(data, location):
    model = model_factory(data, location=location)

    columns = set(model.data_frame.columns)
    assert "datetime" in columns
    assert "target" in columns
    assert "light" in columns
    assert "year" in columns


def test_target_group_is_set_with_integer(data, location):
    """
    Test that given a dataframe and a value for the reference group, we
    produce a new dataframe with the reference group set to 1 and everything
    else set to 0.
    """

    model = model_factory(data, location=location)

    target_group_values = list(model.data_frame["target"])
    race_values = list(model.data_frame["original_target"])
    converted_race_values = [
        1 if x == 1 else 0  # collection
        for x in race_values  # iteration
        ]

    assert converted_race_values == target_group_values


def test_target_group_is_set_with_string(data, location):
    """
    Test that given a dataframe and a value for the reference group, we
    produce a new dataframe with the reference group set to 1 and everything
    else set to 0.
    """
    model = model_factory(data, location=location,
                          columns={"target_column": "gender",
                                   "datetime_column": "datetime"},
                          options={"target_group": "F"})

    target_group_values = list(model.data_frame["target"])
    gender_values = list(model.data_frame["original_target"])
    converted_race_values = [
        1 if x == "F" else 0  # collection
        for x in gender_values  # iteration
        ]

    assert converted_race_values == target_group_values


def test_all_times_in_evening(data, location):
    model = model_factory(data, location=location)
    hours = pd.unique(model.data_frame.datetime.apply(lambda dt: dt.hour))
    assert set(hours).issubset({17, 18, 19, 20, 21})


def test_grey_stops_removed(data, location):
    model = model_factory(data, location=location)
    assert set(pd.unique(model.data_frame['light'])) == {0, 1}


def test_dst_restrict_removes_non_seasonal_stops(data, location):
    model = model_factory(data, location=location,
                          options={"target_group": 1, "dst_restrict": True})

    dst_spring = datetime.datetime(2016, 3, 13, 7, 0)

    assert not model.data_frame.empty
    assert all([(dst_spring - datetime.timedelta(days=30)) <= dt < \
                (dst_spring + datetime.timedelta(days=30))
                for dt in model.data_frame['datetime']])


def test_twilight_range(data, location):
    # Default location is Durham
    model = model_factory(data, location=location)
    min_twilight, max_twilight = model.find_twilight_range()

    assert min_twilight == datetime.time(hour=17, minute=33, second=38)
    assert max_twilight == datetime.time(hour=21, minute=6, second=0)


def test_officerid_is_str(data, location):
    model = model_factory(data, location=location,
                          columns={"target_column": "gender",
                                   "datetime_column": "datetime",
                                   "officer_id_column": "officerid"},
                          options={"target_group": "F"})
    assert all(type(oid) == str for oid in model.data_frame['officerid'])
