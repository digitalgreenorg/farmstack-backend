FROM python:3.8-slim

RUN set -ex \
    && apt-get -y update && apt-get -y upgrade \
    && apt install python3-pip -y


ADD . /datahub
WORKDIR /datahub

# RUN poetry init
RUN python3 -m pip install --upgrade  pip
RUN pip install -r requirements.txt

RUN echo "Hey there **************"

# RUN python manage.py makemigrations \
#     && python manage.py migrate \
#     && python manage.py loaddata db_scripts/userrole_fixture.yaml \
#     && python manage.py loaddata db_scripts/initial_data.yaml

ENV  PYTHONUNBUFFERED 1
# ENV VIRTUAL_ENV /env

# ENV PATH /env/bin:$PATH

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]