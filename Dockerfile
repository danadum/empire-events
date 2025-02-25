FROM python:3.12-alpine AS base

WORKDIR /app

FROM base AS build

RUN python -m venv venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base AS final

COPY --from=build /app/venv venv
ENV PATH="/app/venv/bin:$PATH"

COPY . .

CMD ["python", "main.py"]