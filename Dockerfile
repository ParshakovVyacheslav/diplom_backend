FROM python:latest
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN mkdir -p /app/staticfiles
COPY backend /app/
