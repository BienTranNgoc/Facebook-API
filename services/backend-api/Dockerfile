FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app/services/backend-api

COPY services/backend-api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/backend-api/ ./

EXPOSE 3000
CMD ["python", "manage.py", "runserver", "0.0.0.0:3000"]
