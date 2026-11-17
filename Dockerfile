# syntax=docker/dockerfile:1

# ---- build stage: resolve and install pinned dependencies into a venv -------
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install -r /tmp/requirements.txt

# ---- runtime stage: slim image, non-root user, no build tooling ------------
FROM python:3.13-slim

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    HOME=/home/snaizer

RUN groupadd --gid 10001 snaizer \
    && useradd --uid 10001 --gid snaizer --home-dir /home/snaizer --create-home \
       --shell /usr/sbin/nologin snaizer

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY snaizer_net ./snaizer_net
COPY servers ./servers
COPY content ./content
RUN mkdir -p /app/data && chown snaizer:snaizer /app/data

USER snaizer

EXPOSE 8000 2222
ENV HEALTH_PORT=8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "servers/healthcheck.py"]

CMD ["python", "servers/web.py"]
