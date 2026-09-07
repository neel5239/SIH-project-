from pathlib import Path

path = Path(".\docker-compose.yml")
text = path.read_text(encoding="utf-8")

if "  beat:" in text:
    print("Beat service already exists.")
else:
    marker = '''  worker:
    build: .
    command: celery -A services.m6_platform.queue.celery_app.celery worker --loglevel=INFO
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
'''

    if marker not in text:
        raise RuntimeError("Could not find worker service block")

    beat = marker + '''
  beat:
    build: .
    command: celery -A services.m6_platform.queue.celery_app.celery beat --loglevel=INFO
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
'''

    text = text.replace(marker, beat, 1)
    path.write_text(text, encoding="utf-8")
    print("Celery Beat service added successfully.")
