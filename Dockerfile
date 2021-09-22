FROM python:3

ENV MANAGE_ARG=server

COPY . /app
WORKDIR /app

RUN apt-get update && apt-get install wkhtmltopdf -y --fix-missing

RUN pip install -r requirements.txt

CMD python manage.py ${MANAGE_ARG}