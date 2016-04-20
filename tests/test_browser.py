import pytest
from flask import url_for
from urllib.request import urlopen
import os

browser = pytest.mark.skipif(
    not os.environ.get('BROWSER'),
    reason="need BROWSER set to run"
)


@browser
@pytest.mark.usefixtures('live_server')
class TestLiveServer:
    def test_server_is_up_and_running(self):
        res = urlopen(url_for('star.index', _external=True))
        assert res.code == 200

    def test_splinter_on_index(self, browser):
        browser.visit(url_for('star.index', _external=True))
        assert browser.is_element_present_by_text("start")

