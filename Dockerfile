FROM python:3.11

# ENV no longer adds a layer in new Docker versions,
# so we don't need to chain these in a single line
ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=120

WORKDIR /app
COPY . /app/

RUN pip install .

EXPOSE 80

CMD hypercorn backend_test.api:app --bind '[::]:80'
