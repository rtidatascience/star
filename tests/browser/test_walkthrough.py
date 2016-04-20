import pytest
from flask import url_for
import os

browser = pytest.mark.skipif(
    not os.environ.get('BROWSER'),
    reason="need BROWSER set to run"
)

dir = os.path.dirname(__file__)
filename = os.path.join(dir, '..', "sample_data/datetime-race-gender-make.csv")

@browser
@pytest.mark.usefixtures('live_server')
class TestWalkthrough:
    def click_button(self, browser):
        button = browser.find_by_tag("button").first
        button.click()

    def test_full_walkthrough(self, browser):
        browser.visit(url_for('star.location', _external=True))
        browser.fill('location', "Durham, NC, USA")
        self.click_button(browser)

        browser.attach_file('records', filename)
        self.click_button(browser)

        browser.select("date_column", "datetime")
        browser.select("time_column", "datetime")
        browser.select("target_column", "race")
        self.click_button(browser)

        browser.choose("target_group", 0)
        self.click_button(browser)

        assert browser.status_code.is_success()
        assert browser.is_element_present_by_text("How we calculated your results")

    def test_changing_columns(self, browser):
        browser.visit(url_for('star.location', _external=True))
        browser.fill('location', "Durham, NC, USA")
        self.click_button(browser)

        browser.attach_file('records', filename)
        self.click_button(browser)

        browser.select("date_column", "datetime")
        browser.select("time_column", "datetime")
        browser.select("target_column", "gender")
        self.click_button(browser)

        browser.find_by_id("change_columns").click()

        browser.select("date_column", "datetime")
        browser.select("time_column", "datetime")
        browser.select("target_column", "race")
        self.click_button(browser)

        assert browser.status_code.is_success()
        assert browser.url[-9:] == "/options/"
