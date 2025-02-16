FROM public.ecr.aws/lambda/python:3.11

RUN cat /etc/system-release \
    && yum install -y unzip libpq-devel git \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && aws --version \
    && curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python \
    && cd /usr/local/bin \
    && ln -s /opt/poetry/bin/poetry
ENV PYTHONUTF8=1

COPY pyproject.toml poetry.toml poetry.lock ${LAMBDA_TASK_ROOT}/
RUN pip install --upgrade pip \
    && poetry config virtualenvs.create false \
    && poetry install --no-root --only main

COPY src/ ${LAMBDA_TASK_ROOT}/
