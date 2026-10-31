FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["sh", "-c", "flask --app app db upgrade && gunicorn --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --access-logfile - run:app"]
