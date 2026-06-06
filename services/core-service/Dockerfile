FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app
COPY services/core-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY services/core-service/ ./
EXPOSE 3002
CMD ["python", "app.py"]
