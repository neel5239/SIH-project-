FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn[standard]==0.34.0
COPY server.py .
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
