FROM python:3.12-slim
RUN useradd --system --uid 10001 app && mkdir -p /app /data && chown 10001:10001 /data
WORKDIR /app
COPY shared/relay.py /app/relay.py
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["python3", "/app/relay.py", "--host", "0.0.0.0", "--port", "8000", "--data", "/data/relay.sqlite"]
CMD ["--release", "container-v1"]
