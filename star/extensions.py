# -*- coding: utf-8 -*-
"""Extensions module."""

from flask.ext.appconfig import AppConfig

config = AppConfig()

from flask.ext.assets import Environment, Bundle

assets = Environment()

js = Bundle('vendor/jquery-2.2.0.js', 'vendor/theme-dashboard/dist/toolkit.js',
            'vendor/jquery.color-2.1.2.js', 'app.js',
            filters='rjsmin', output='gen/packed.js')
css = Bundle('vendor/theme-dashboard/dist/toolkit-light.css', 'style.css', filters='cssmin',
             output='gen/packed.css')
assets.register('js_all', js)
assets.register('css_all', css)

from flask_mail import Mail
mail = Mail()

from raven.contrib.flask import Sentry
from .default_config import SENTRY_DSN
sentry = Sentry(dsn=SENTRY_DSN)
