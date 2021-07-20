#!/usr/bin/env python
import os

from flask_script import Manager, Shell, Server
from flask_script.commands import ShowUrls, Clean

from werkzeug.middleware.profiler import ProfilerMiddleware

from star import create_app


app = create_app()
manager = Manager(app)
manager.add_command('server', Server(host="0.0.0.0", port=5000))
manager.add_command('show-urls', ShowUrls())
manager.add_command('clean', Clean())


@manager.shell
def make_shell_context():
    """ Creates a python REPL with several default imports
        in the context of the app
    """

    return dict(app=app)

@manager.command
def profile():
    app.config['PROFILE'] = True
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    app.run(debug=True, host="0.0.0.0")


if __name__ == '__main__':
    manager.run()