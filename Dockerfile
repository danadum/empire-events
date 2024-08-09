FROM python:3.10-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt


FROM python:3.10-alpine

WORKDIR /bot

COPY --from=build /opt/venv /bot/venv
ENV PATH="/bot/venv/bin:$PATH"

COPY . /bot
CMD python main.py