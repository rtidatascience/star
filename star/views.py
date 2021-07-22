import hashlib
import io
import os
import sqlite3
import pdfkit
import tempfile

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from werkzeug.routing import RequestRedirect

from flask import Blueprint, flash, request, current_app, render_template, \
    redirect, url_for, session, g, Response, make_response, send_file
from flask_mail import Message
from star.analysis import Analysis
from .extensions import sentry, mail
from .models import VODModel, load_csv_as_dataframe, Location, EmptyModel, \
    pickle_dataframe, clear_pickle

star = Blueprint("star", __name__)

ALLOWED_EXTENSIONS = ['.csv']
BLOCKSIZE = 65536


def connect_to_database():
    database = current_app.config['DATABASE']
    return sqlite3.connect(database)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db


@star.before_app_first_request
def init_db():
    print("init_db")
    db = get_db()
    c = db.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS emails
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
     email TEXT NOT NULL,
     optin BOOLEAN NOT NULL DEFAULT FALSE,
     title TEXT NULL,
     name TEXT NULL,
     organization TEXT NULL,
     datetime TEXT NOT NULL)
    """)


@star.teardown_request
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def allowed_file(filename):
    path = Path(filename)
    return path.suffix and path.suffix in ALLOWED_EXTENSIONS


def get_location():
    try:
        return session['location']
    except KeyError:
        flash("Please enter your location.")
        raise RequestRedirect(url_for('star.location'))


def get_filename():
    try:
        return session['filename']
    except KeyError:
        flash("Please upload your traffic stop records.")
        raise RequestRedirect(url_for('star.upload'))


def get_file():
    filename = get_filename()
    path = Path(os.path.join(current_app.config['UPLOAD_DIR'], filename))
    if not path.is_file():
        flash("There was a problem reading this file.", category="danger")
        raise RequestRedirect(url_for('star.upload'))
    return path


def get_columns():
    try:
        return session['columns']
    except KeyError:
        flash("Please select the columns to use for your records.")
        raise RequestRedirect(url_for("star.columns"))


def get_options():
    try:
        return session['options']
    except KeyError:
        flash("Please select the options to use for your analysis.")
        raise RequestRedirect(url_for("star.options"))


def clear_session(step):
    steps = ["location", "filename", "columns", "options"]
    step_idx = steps.index(step)
    for step in steps[step_idx:]:
        session.pop(step, None)


@star.route("/")
def index():
    return render_template("index.html")


@star.route("/terms/")
def terms():
    return render_template("terms.html")


# Step 1
@star.route("/location/", methods=["GET", "POST"])
def location():
    error = None

    if request.method == "POST":
        location_name = request.form['location']

        if location_name:
            possible_locations = Location.geolocate(location_name)

            if len(possible_locations) == 0:
                error = "We could not find that location."
            elif len(possible_locations) == 1:
                session['location'] = possible_locations[0].as_dict()
                return redirect(url_for("star.upload"))
            else:
                return render_template("multiple_locations.html",
                                       locations=possible_locations)
        else:
            error = "Please enter a city."

    clear_session("location")
    return render_template("location.html", error=error)


# Step 2
@star.route("/upload/", methods=["GET", "POST"])
def upload():
    get_location()
    error = None

    if request.method == "POST":
        file = request.files['records']
        if file and allowed_file(file.filename):
            path = Path(file.filename)
            hasher = hashlib.sha256()
            buf = file.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = file.read(BLOCKSIZE)
            filename = hasher.hexdigest() + path.suffix
            file.seek(0)
            file.save(os.path.join(current_app.config['UPLOAD_DIR'], filename))

            session['original_filename'] = os.path.basename(file.filename)
            session['filename'] = filename
            return redirect(url_for('star.columns'))
        else:
            error = "Please upload a CSV file."

    clear_session("filename")
    return render_template("upload.html", error=error)


# Step 3
@star.route("/columns/", methods=["GET", "POST"])
def columns():
    location = get_location()
    path = get_file()
    clear_pickle(path)
    error = None

    if request.method == "POST":
        date_column = request.form['date_column']
        time_column = request.form['time_column']
        target_column = request.form['target_column']
        officer_id_column = request.form.get('officer_id_column')

        if date_column == time_column:
            datetime_column = date_column
            datetime_columns = [date_column]
        else:
            datetime_column = "__datetime"
            datetime_columns = {"__datetime": [date_column, time_column]}

        cols = {
            "datetime_column": datetime_column,
            "datetime_columns": datetime_columns,
            "date_column": date_column,
            "time_column": time_column,
            "target_column": target_column,
            "officer_id_column": officer_id_column,
        }

        df = load_csv_as_dataframe(path, cols)
        pickle_dataframe(path, df)

        if df[datetime_column].dtype == np.dtype('datetime64[ns]'):
            session['columns'] = cols
            return redirect(url_for('star.options'))
        else:
            error = "We could not parse your date and time columns. See the " \
                    "instructions for some examples of good date and time " \
                    "columns."
            for index, value in df[datetime_column].iteritems():
                try:
                    pd.to_datetime(value)
                except (ValueError, TypeError) as ex:
                    error = ("We could not parse your date and time columns on "
                             "line {}. The value we read "
                             "was \"{}\".").format(index + 2, value)
                    error += " See the instructions for some examples of " \
                             "good date and time columns. "
                    break

            if not current_app.config['DEBUG']:
                sentry.captureMessage("Could not parse date and time columns.",
                                      data={
                                          "dtype": df[datetime_column].dtype,
                                          "sample": df[datetime_column][0],
                                      })

    clear_session("columns")

    df = load_csv_as_dataframe(path, pickled=False)
    session["record_count"] = len(df.index)
    cols = list(df.columns)
    sample = df[0:5].values.tolist()

    return render_template("columns.html",
                           error=error,
                           cols=cols,
                           sample=sample)


# Step 4
@star.route("/options/", methods=["GET", "POST"])
def options():
    get_location()
    path = get_file()
    cols = get_columns()

    if request.method == "POST":
        options = {
            "target_group": request.form['target_group'],
            "dst_restrict": bool(request.form.get('dst_restrict'))
        }

        session['options'] = options

        return redirect(url_for('star.analyze'))

    clear_session("options")

    df = load_csv_as_dataframe(path, cols)
    target_opts = pd.unique(df[cols["target_column"]])
    return render_template("options.html", target_opts=target_opts)


# Step 5
@star.route("/analyze/", methods=["GET"])
def analyze():
    location = get_location()
    path = get_file()
    filename = session['original_filename']
    cols = get_columns()
    options = get_options()
    df = load_csv_as_dataframe(path, cols)

    try:
        model = VODModel(df, location=location, columns=cols, options=options)
    except EmptyModel:
        flash(
            "You had no records after filtering. Try not restricting to "
            "daylight savings time transition times or upload more records.")
        return redirect(url_for('star.options'))

    try:
        analysis = Analysis()
        results = analysis.analyze(model.data_frame)
    except Exception:
        results = {
            "error": "We ran into some trouble while analyzing your data. "
                     "This can be caused by having too little data. We've "
                     "recorded the error and will investigate it further. If "
                     "you have any questions, please email toolhelp@rti.org."
        }
        sentry.captureException(extra=session)

    min_twilight, max_twilight = model.find_twilight_range()
    itp_range = "{} - {}".format(min_twilight.strftime("%H:%M:%S"),
                                 max_twilight.strftime("%H:%M:%S"))

    min_date, max_date = model.find_date_range()
    date_range = "{} - {}".format(min_date.strftime("%x"),
                                  max_date.strftime("%x"))

    return render_template("analyze.html",
                           datetime=datetime.now().strftime("%x %X %Z"),
                           location=location,
                           original_filename=filename,
                           original_record_count=len(df.index),
                           final_record_count=len(model.data_frame.index),
                           date_range=date_range,
                           itp_range=itp_range,
                           light_count=model.light_count(),
                           dark_count=model.dark_count(),
                           results=results)


# Step 6
@star.route("/download/", methods=["GET"])
def download():
    location = get_location()
    path = get_file()
    cols = get_columns()
    options = get_options()
    df = load_csv_as_dataframe(path, cols)
    model = VODModel(df, location=location, columns=cols, options=options)

    stringio = io.StringIO()
    model.data_frame.to_csv(stringio, index=False)
    stringio.seek(0)

    try:
        export_path = os.path.splitext(session['original_filename'])[
                          0] + "-export_for_analysis.csv"
    except Exception:
        export_path = "export_for_analysis.csv"

    output = make_response(stringio.getvalue())
    output.headers[
        "Content-Disposition"] = "attachment; filename=" + export_path
    output.headers["Content-type"] = "text/csv"
    return output

    response = Response(generate(), mimetype='text/csv')
    response.headers[
        'Content-Disposition'] = 'attachment; filename=' + export_path
    return response


@star.route("/email/", methods=["POST"])
def email():
    location = get_location()
    path = get_file()
    filename = session['original_filename']
    cols = get_columns()
    options = get_options()
    df = load_csv_as_dataframe(path, cols)

    email = request.form.get('email')
    if not email:
        flash("Email is required.", category="danger")
        raise RequestRedirect(url_for('star.analyze'))

    optin = bool(request.form.get('optin', False))
    title = request.form.get('title')
    name = request.form.get('name')
    organization = request.form.get('organization')

    db = get_db()
    c = db.cursor()

    c.execute("""
    INSERT INTO emails (email, optin, title, name, organization, datetime)
    VALUES(?, ?, ?, ?, ?, ?)
    """, (email, optin, title, name, organization, datetime.now()))
    db.commit()

    model = VODModel(df, location=location, columns=cols, options=options)
    analysis = Analysis()
    results = analysis.analyze(model.data_frame)
    min_twilight, max_twilight = model.find_twilight_range()
    itp_range = "{} - {}".format(min_twilight.strftime("%H:%M:%S"),
                                 max_twilight.strftime("%H:%M:%S"))

    min_date, max_date = model.find_date_range()
    date_range = "{} - {}".format(min_date.strftime("%x"),
                                  max_date.strftime("%x"))

    params = dict(datetime=datetime.now().strftime("%x %X %Z"),
                  location=location,
                  original_filename=filename,
                  cols=cols,
                  options=options,
                  original_record_count=len(df.index),
                  final_record_count=len(model.data_frame.index),
                  date_range=date_range,
                  itp_range=itp_range,
                  light_count=model.light_count(),
                  dark_count=model.dark_count(),
                  results=results,
                  root_dir=current_app.config['ROOT_DIR'])

    pdf_html = render_template("email.html", **params)

    # return pdf_html

    options = {
        'page-size': 'Letter',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8"
    }

    directory = tempfile.mkdtemp()
    pdffile = os.path.join(directory, "out.pdf")
    pdf = pdfkit.from_string(pdf_html, pdffile, options=options)

    msg = Message("RTI-STAR Report for {}".format(name or email),
                  recipients=[email])
    msg.body = "Your report is attached."
    with current_app.open_resource(pdffile) as fp:
        msg.attach("report.pdf", "application/pdf", fp.read())
    mail.send(msg)

    flash("Your email has been sent.")
    return redirect(url_for('star.analyze'))


def flash_errors(form, category="warning"):
    '''Flash all errors for a form.'''
    for field, errors in form.errors.items():
        for error in errors:
            flash("{0} - {1}"
                  .format(getattr(form, field).label.text, error), category)
