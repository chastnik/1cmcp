FROM python:3.12-slim

WORKDIR /app

COPY gateway /app/gateway
COPY specs /app/specs

RUN pip install --no-cache-dir /app/gateway

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-m", "onecmcp", "serve", "--host", "0.0.0.0", "--port", "8000"]
