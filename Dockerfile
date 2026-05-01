FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY scripts/start-api.sh scripts/start-ui.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-api.sh /usr/local/bin/start-ui.sh

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000 8501

# Default: API (Render/Fly inject PORT; local Docker Compose defaults to 8000)
CMD ["start-api.sh"]
