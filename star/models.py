"""Add your models here."""
import datetime as dt

import astral
import googlemaps
import pandas as pd
import pytz

from star.default_config import GOOGLE_MAPS_API_KEY


def load_csv_as_dataframe(path, columns=None, pickled=True):
    if pickled and path.with_suffix('.pkl').is_file():
        return pd.read_pickle(str(path.with_suffix('.pkl')))

    if columns:
        usecols = [columns['date_column'], columns['time_column'],
                   columns['target_column']]
        if columns.get('officer_id_column'):
            usecols.append(columns['officer_id_column'])
        return pd.read_csv(path,
                           parse_dates=columns['datetime_columns'],
                           # usecols=usecols,
                           )
    else:
        return pd.read_csv(path)


def pickle_dataframe(path, dataframe):
    return dataframe.to_pickle(str(path.with_suffix('.pkl')))


def clear_pickle(path):
    pickle = path.with_suffix('.pkl')
    if pickle.exists():
        pickle.unlink()


def within_dst_range(datetime, transition_dates):
    return any(
        (td - dt.timedelta(days=30)) <= datetime < (td + dt.timedelta(days=30))
        for td in transition_dates)


class EmptyModel(Exception):
    pass


class VODModel:
    def __init__(self, data_frame, location, columns, options):
        self.location = Location(**location)
        self.dst_restrict = bool(options.get("dst_restrict"))
        self.target_column = columns["target_column"]
        self.target_group = options["target_group"]
        self.officer_id_column = columns.get("officer_id_column")
        self.datetime_column = columns["datetime_column"]
        self.data_frame = self.generate_data_frame(data_frame, debug=True)

    def find_date_range(self):
        df = self.data_frame
        dates = pd.unique(df.datetime.dropna().apply(lambda dt: dt.date()))
        return min(dates), max(dates)

    def find_twilight_range(self, start_year=None, stop_year=None):
        if start_year is None or stop_year is None:
            df = self.data_frame
            years = pd.unique(df.datetime.dropna().apply(lambda dt: dt.year))
            min_year = min(years)
            max_year = max(years)
            if min_year > max_year - 5:
                min_year = max_year - 5
            if start_year is None:
                start_year = min_year
            if stop_year is None:
                stop_year = max_year

        solstice_dates = [{"month": 6, "day": 20}, {"month": 12, "day": 21}]
        twilights = []
        for year in range(start_year, stop_year + 1):
            for date in solstice_dates:
                for delta in range(-30,30):
                    dusk = self.location.dusk(
                        date=dt.date(year=year, month=date["month"],
                                     day=date["day"]) + dt.timedelta(days=delta))
                    twilights.append(dusk.time())
        return min(twilights), max(twilights)

    def light_count(self):
        df = self.data_frame
        return len(df[df.light == 1])

    def dark_count(self):
        df = self.data_frame
        return len(df[df.light == 0])

    def generate_data_frame(self, df, debug=False):
        def convert_to_target_group(value):
            return 1 if str(value) == str(self.target_group) else 0

        def convert_to_light(value):
            light_aware_date_time = LightAwareDatetime(value, self.location)
            if light_aware_date_time.is_light():
                return 1
            elif light_aware_date_time.is_dark():
                return 0
            else:
                return -1

        def convert_to_dusk(value):
            light_aware_date_time = LightAwareDatetime(value, self.location)
            return self.location.dusk(date=light_aware_date_time.date)

        import time
        start = time.time()

        def timecheck(note=None):
            if debug:
                print(note, time.time() - start)

        if self.datetime_column != "datetime":
            if "datetime" in df.columns:
                df.drop("datetime", axis=1, inplace=True)
            df.rename(columns={self.datetime_column: "datetime"}, inplace=True)

        timecheck("Before dropping na rows")
        df.dropna(how="any", subset=["datetime", self.target_column],
                  inplace=True)
        timecheck("After dropping na rows")

        # set index to datetime
        timecheck("Before setting index")
        df.index = df.datetime
        timecheck("After setting index")

        timecheck("Before stripping non-evening hours")
        df = self._strip_non_evening_hours(df)
        timecheck("After stripping non-evening hours")

        if self.dst_restrict:
            timecheck("Before stripping non-seasonal days")
            df = self._strip_non_seasonal_days(df)
            df = self._strip_based_on_min_max_twilight(df)
            timecheck("After stripping non-seasonal days")

        timecheck("Before converting to target group")
        if "original_target" in df.columns:
            df.drop("original_target", axis=1, inplace=True)
        df.rename(columns={self.target_column: "original_target"}, inplace=True)
        if "target" in df.columns:
            df.drop("target", axis=1, inplace=True)
        df["target"] = df["original_target"].apply(convert_to_target_group)
        timecheck("After converting to target group")

        timecheck("Before converting to light")
        df["light"] = df["datetime"].apply(convert_to_light)
        if debug:
            df["dusk"] = df["datetime"].apply(convert_to_dusk)
        timecheck("After converting to light")
        timecheck("Before stripping twilight hours")
        df = self._strip_grey_hours(df)
        timecheck("After stripping twilight hours")

        timecheck("Before creating year column")
        df["year"] = df["datetime"].apply(lambda dt: dt.year)
        timecheck("After creating year column")

        df["month"] = df["datetime"].apply(lambda dt: dt.month)
        df["day_of_week"] = df["datetime"].apply(lambda dt: dt.isoweekday())

        def time_in_seconds(dt):
            start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            return int(dt.timestamp() - start_of_day.timestamp())

        df["time_in_seconds"] = df["datetime"].apply(time_in_seconds)

        if self.officer_id_column:
            df.rename(columns={self.officer_id_column: "officerid"},
                      inplace=True)
            df.officerid = df.officerid.apply(str)

        return df

    def _strip_non_seasonal_days(self, df):
        """
        Strip days that are not within +/- 30 days of daylight savings time
        transition days.
        """
        tz = pytz.timezone(self.location.timezone)

        # Set the unique set of years in our data frame.
        years = set(pd.unique(df.datetime.apply(lambda dt: dt.year)))

        # Get the DST transition dates for those years.
        dst_transition_dates = [
            dt for dt in tz._utc_transition_times if dt.year in years]

        in_dates = df.datetime.apply(
            lambda dt: within_dst_range(dt, dst_transition_dates))

        df = df[in_dates]
        if df.empty:
            raise EmptyModel
        return df.copy()

    def _strip_based_on_min_max_twilight(self, df):
        dates = pd.unique(df.datetime.dropna().apply(lambda dt: dt.date()))
        dusks = [self.location.dusk(date).time() for date in dates]
        min_twilight = min(dusks)
        max_twilight = max(dusks)

        df = df.iloc[
            df.index.indexer_between_time(min_twilight,
                                          max_twilight,
                                          include_end=True)]
        if df.empty:
            raise EmptyModel

        return df.copy()

    def _strip_non_evening_hours(self, df):
        years = pd.unique(df.datetime.dropna().apply(lambda dt: dt.year))
        min_year = min(years)
        max_year = max(years)
        if min_year > max_year - 5:
            min_year = max_year - 5
        min_twilight, max_twilight = self.find_twilight_range(min_year,
                                                              max_year)
        df = df.iloc[
            df.index.indexer_between_time(min_twilight,
                                          max_twilight,
                                          include_end=True)]
        if df.empty:
            raise EmptyModel

        return df.copy()

    def _strip_grey_hours(self, df):
        df = df[df.light != -1]
        if df.empty:
            raise EmptyModel
        return df.copy()


GMaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

from functools import lru_cache


class Location:
    def __init__(self, latitude, longitude, **kwargs):
        location_tuple = (kwargs.get('name'),
                          kwargs.get('region'),
                          latitude,
                          longitude,
                          kwargs.get('timezone'),
                          kwargs.get('elevation'))
        self.has_elevation = "elevation" in kwargs
        self.has_timezone = "timezone" in kwargs

        self.location = astral.Location(location_tuple)

    def __getattr__(self, name):
        return getattr(self.location, name)

    def __hash__(self):
        return self.location.__hash__()

    @lru_cache()
    def sunrise(self, date, local=True):
        return self.location.sunrise(local=local, date=date)

    @lru_cache()
    def sunset(self, date, local=True):
        return self.location.sunset(local=local, date=date)

    @lru_cache()
    def dawn(self, date, local=True):
        return self.location.dawn(local=local, date=date)

    @lru_cache()
    def dusk(self, date, local=True):
        return self.location.dusk(local=local, date=date)

    @classmethod
    def geolocate(cls, name):
        results = googlemaps.geocoding.geocode(GMaps,
                                               address=name)

        locations = [Location(latitude=result['geometry']['location']['lat'],
                              longitude=result["geometry"]['location']["lng"],
                              name=result['formatted_address'])
                     for result in results
                     if "locality" in result["types"]
                     or "administrative_area_level_3" in result["types"]]

        return locations

    @property
    def timezone(self):
        if not self.has_timezone:
            result = googlemaps.timezone.timezone(GMaps,
                                                  (self.latitude,
                                                   self.longitude))
            self.location.timezone = result['timeZoneId']
            self.has_timezone = True

        return self.location.timezone

    @property
    def elevation(self):
        if not self.has_elevation:
            results = googlemaps.elevation.elevation(GMaps,
                                                     (self.latitude,
                                                      self.longitude))
            self.location.elevation = results[0]['elevation']
            self.has_elevation = True

        return self.location.elevation

    def __eq__(self, other):
        if not type(self) == type(other):
            return False

        return self.latitude == other.latitude and \
               self.longitude == other.longitude

    def as_dict(self):
        return {
            "name": self.name,
            "region": self.region,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "elevation": self.elevation,
        }

    def __str__(self):
        return self.name


class LightAwareDatetime:
    def __init__(self, datetime, location):
        self.location = location

        # localize datetime by getting the timezone and applying it
        timezone = pytz.timezone(self.location.timezone)
        datetime = datetime.to_pydatetime()
        self.datetime = timezone.localize(datetime)
        self.date = self.datetime.date()

    def is_light(self):
        sunrise = self.location.sunrise(local=True,
                                        date=self.date)
        sunset = self.location.sunset(local=True, date=self.date)
        return sunrise <= self.datetime <= sunset

    def is_dark(self):
        dawn = self.location.dawn(local=True, date=self.date)
        dusk = self.location.dusk(local=True, date=self.date)
        return self.datetime < dawn or dusk <= self.datetime

    def is_twilight(self):
        dawn = self.location.dawn(local=True, date=self.date)
        sunrise = self.location.sunrise(local=True,
                                        date=self.date)
        sunset = self.location.sunset(local=True, date=self.date)
        dusk = self.location.dusk(local=True, date=self.date)

        return (dawn <= self.datetime < sunrise) or \
               (sunset <= self.datetime < dusk)
