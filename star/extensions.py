# -*- coding: utf-8 -*-
"""Extensions module."""

from flask_appconfig import AppConfig

config = AppConfig()

from flask_assets import Environment, Bundle

assets = Environment()

js = Bundle(
    "vendor/jquery-3.6.0.js",
    "vendor/jquery.color-2.1.2.js",
    "vendor/bootstrap/js/bootstrap.js",
    "app.js",
    filters="rjsmin",
    output="gen/packed.js",
)
css = Bundle(
    "vendor/bootstrap/css/bootstrap.css",
    "style.css",
    filters="cssmin",
    output="gen/packed.css",
)
assets.register("js_all", js)
assets.register("css_all", css)

from flask_mail import Mail

mail = Mail()

from raven.contrib.flask import Sentry
from .default_config import SENTRY_DSN

sentry = Sentry(dsn=SENTRY_DSN)
