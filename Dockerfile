FROM python:3.8-slim

RUN set -ex \
    && apt-get -y update && apt-get -y upgrade \
    && apt install python3-pip -y \
    && apt install curl -y \
    && DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker} \
    && mkdir -p $DOCKER_CONFIG/cli-plugins \
    && curl -SL https://github.com/docker/compose/releases/download/v2.2.3/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose \
    && chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose


ADD . /datahub
WORKDIR /datahub

# RUN poetry init
RUN python3 -m pip install --upgrade  pip
RUN pip install -r requirements.txt

# RUN python manage.py makemigrations \
#     && python manage.py migrate \
#     && python manage.py loaddata db_scripts/userrole_fixture.yaml \
#     && python manage.py loaddata db_scripts/initial_data.yaml

ENV  PYTHONUNBUFFERED 1
# ENV VIRTUAL_ENV /env

# ENV PATH /env/bin:$PATH

EXPOSE 8000


CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
