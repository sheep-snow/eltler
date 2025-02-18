FROM python:3.11

ENV PYTHONUNBUFFERED 1
ENV PYTHONUTF8=1

WORKDIR /app
RUN apt-get update
RUN apt-get install unzip curl -y \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && aws --version \
    && curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python \
    && cd /usr/local/bin \
    && ln -s /opt/poetry/bin/poetry

COPY pyproject.toml poetry.toml poetry.lock ./
RUN pip install --upgrade pip \
    && poetry config virtualenvs.create false \
    && poetry install --no-root --only main

COPY src/ /app/
CMD [ "firehose.listener.main" ]