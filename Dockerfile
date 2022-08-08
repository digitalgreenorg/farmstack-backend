FROM python:3.8-slim

# ADD requirements.txt /FS_API/requirements.txt

RUN set -ex \
    && apt-get -y update && apt-get -y upgrade \
    #  && apt-get install -y default-libmysqlclient-dev python3-dev gcc\
    # && python3 -m venv /env \
    && apt install python3-pip -y
# && pip install poetry \
# && apt install curl -y 
# && pip install -r requirements.txt
# && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python - \
# && POETRY_HOME=/etc/poetry python get-poetry.py \
# && . $HOME/.poetry/env \

ADD . /datahub
WORKDIR /datahub

# RUN poetry init
RUN python3 -m pip install --upgrade  pip
RUN pip install -r requirements.txt

ENV  PYTHONUNBUFFERED 1
# ENV VIRTUAL_ENV /env

# ENV PATH /env/bin:$PATH

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "127.0.0.1:8000"]