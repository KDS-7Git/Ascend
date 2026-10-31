FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY ascend ./ascend
COPY web ./web
COPY packs/community ./packs/community
RUN --mount=type=bind,source=docker,target=/build \
    if [ -d /build/wheelhouse ]; then \
      PIP_NO_INDEX=1 PIP_FIND_LINKS=/build/wheelhouse pip install '.[server]'; \
    else pip install --no-cache-dir '.[server]'; fi \
    && useradd --uid 10001 --create-home ascend && mkdir /data && chown ascend:ascend /data
USER ascend
ENV ASCEND_HOME=/data
VOLUME ["/data"]
EXPOSE 8420
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8420/api/health')" || exit 1
CMD ["ascend-server", "--host", "0.0.0.0", "--port", "8420"]
