# pull official base image
FROM python:3.8.3-alpine
# set work directory
WORKDIR /usr/src/app
# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# install dependencies
RUN pip install --upgrade pip
#COPY ./kpalch/requirements.txt .
COPY ./ .
RUN pip install -r requirements.txt
# copy project
#COPY ./kpalch/ .

RUN python manage.py makemigrations
RUN python manage.py migrate