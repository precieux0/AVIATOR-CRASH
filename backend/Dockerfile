FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
RUN mkdir -p /app/data
ENV PYTHONUNBUFFERED=1
# Use PORT env var (Render provides it). Fall back to 8000 if not set.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
