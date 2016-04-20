import vcr
from star.models import Location


@vcr.use_cassette('vcr_cassettes/geocoding.yaml', record_mode="new_episodes")
def test_geocoding():
    locations = Location.geolocate("Durham")
    assert len(locations) == 6
    assert Location(latitude=35.9940329, longitude=-78.898619) in locations


@vcr.use_cassette('vcr_cassettes/timezone.yaml', record_mode="new_episodes")
def test_timezone():
    location = Location(name="Durham, NC", latitude=35.9940329,
                        longitude=-78.898619)
    assert location.timezone == "America/New_York"


@vcr.use_cassette('vcr_cassettes/elevation.yaml', record_mode="new_episodes")
def test_elevation():
    location = Location(name="Durham, NC", latitude=35.9940329,
                        longitude=-78.898619)
    assert location.elevation == 120

