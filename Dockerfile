FROM python:3.12-alpine
WORKDIR /app
COPY . .
RUN --mount=type=bind,from=ghcr.io/astral-sh/uv:0.13.9,source=/uv,target=/bin/uv \
    --mount=type=secret,id=extra_ca \
    if [ -f /run/secrets/extra_ca ]; then \
        cat /etc/ssl/certs/ca-certificates.crt /run/secrets/extra_ca > /tmp/build-ca.crt; \
        SSL_CERT_FILE=/tmp/build-ca.crt uv sync --no-cache --frozen --no-dev || exit $?; \
        rm /tmp/build-ca.crt; \
    else uv sync --no-cache --system-certs --frozen --no-dev || exit $?; fi \
    && adduser -S -D contour \
    && chmod -R a+rX /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH="/app/src" PYTHONUNBUFFERED="1"
USER contour
