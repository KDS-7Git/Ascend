ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}
WORKDIR /app
COPY shared/relay.py /app/relay.py
RUN mkdir /data && chown 65532:65532 /data
USER 65532:65532
EXPOSE 8000
CMD ["python", "/app/relay.py", "--host", "0.0.0.0", "--port", "8000", "--data", "/data/relay.sqlite", "--release", "container-v1"]
