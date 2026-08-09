FROM python:3.14-slim

WORKDIR /app
COPY tasklite_exporter.py /app/tasklite_exporter.py
ENV PYTHONUNBUFFERED=1
EXPOSE 9460
CMD ["python3", "/app/tasklite_exporter.py"]
