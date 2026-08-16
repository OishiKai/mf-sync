ARG PYTHON_BUILD_IMAGE=python:3.13-slim-trixie@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a
ARG PYTHON_RUNTIME_IMAGE=gcr.io/distroless/python3-debian13:nonroot@sha256:eff0a6050f5ea9e8154c3d137d468901864803ce3c7f4657d419e64f3f1f8b40

FROM ${PYTHON_BUILD_IMAGE} AS dependencies

WORKDIR /build
COPY requirements.lock ./
RUN python -m pip install \
    --no-cache-dir \
    --require-hashes \
    --target /opt/python \
    --requirement requirements.lock

FROM ${PYTHON_RUNTIME_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/python

WORKDIR /app

COPY --from=dependencies /opt/python /opt/python
COPY app ./app

USER 65532:65532

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()"]

CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
