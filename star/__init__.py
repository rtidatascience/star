from flask import Flask
import os

from . import models
from .extensions import config, assets, sentry, mail
from .views import star

DEBUG = True
ASSETS_DEBUG = True
SECRET_KEY = 'development-key'
UPLOAD_DIR = "/tmp/flask-uploads/"
ROOT_DIR = os.path.realpath(os.path.dirname(__file__))

def create_app():
    app = Flask(__name__)
    app.config.from_object(__name__)
    app.register_blueprint(star)

    config.init_app(app)
    assets.init_app(app)
    mail.init_app(app)

    if not app.config['DEBUG']:
        sentry.init_app(app)

    make_upload_dir(app)
    return app


def make_upload_dir(app):
    if os.path.exists(app.config['UPLOAD_DIR']):
        if os.path.isdir(app.config['UPLOAD_DIR']):
            return
        else:
            os.remove(app.config['UPLOAD_DIR'])

    os.mkdir(app.config['UPLOAD_DIR'])
