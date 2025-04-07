# ------------ Stage 1: Build dependencies -------------
FROM python:3.11-slim as builder

# Install dependencies
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 libsasl2-dev curl gcc libldap2-dev libpq-dev python3-dev\

    && DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker} \
    && mkdir -p $DOCKER_CONFIG/cli-plugins \
    && curl -SL https://github.com/docker/compose/releases/download/v2.2.3/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose \
    && chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

# Install build tools and system dependencies
RUN apt-get update && apt-get install -y \
    build-essential gcc curl libpq-dev libsasl2-dev libldap2-dev python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install python-ldap==3.3.1 \
    && pip install --upgrade pyopenssl \
    && pip install -r requirements.txt

# ------------ Stage 2: Final minimal image -------------
FROM python:3.11-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg libsm6 libxext6 libsasl2-dev libldap2-dev libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy app source code
COPY . .

ENV PYTHONUNBUFFERED 1

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
