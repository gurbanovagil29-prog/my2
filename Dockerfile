FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# База (что уже отправлено) хранится в /app/data, чтобы переживать перезапуск контейнера
CMD ["sh", "-c", "python -m scanner --config config.yaml"]
