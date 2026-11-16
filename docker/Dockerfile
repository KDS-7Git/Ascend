FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159
ARG ASCEND_OFFLINE=0
WORKDIR /app
COPY docker/constraints.txt ./constraints.txt
COPY pyproject.toml setup.py MANIFEST.in README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY ascend ./ascend
COPY web ./web
COPY packs/community ./packs/community
RUN --mount=type=bind,source=docker,target=/build \
    if [ "$ASCEND_OFFLINE" = 1 ]; then \
      export PIP_NO_INDEX=1 PIP_FIND_LINKS=/build/wheelhouse; \
    fi \
    && pip install --no-cache-dir -c constraints.txt setuptools wheel \
    && pip install --no-cache-dir --no-build-isolation -c constraints.txt '.[server,push]' \
    && useradd --uid 10001 --create-home ascend && mkdir /data && chown ascend:ascend /data
USER ascend
ENV ASCEND_HOME=/data
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
VOLUME ["/data"]
EXPOSE 8420
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8420/api/health')" || exit 1
CMD ["ascend-server", "--host", "0.0.0.0", "--port", "8420"]
