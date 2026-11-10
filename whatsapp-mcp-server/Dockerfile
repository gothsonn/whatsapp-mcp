FROM ghcr.io/astral-sh/uv:0.5.31-python3.11-bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home --home-dir /home/mcp mcp
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY *.py ./
RUN chown -R mcp /app
USER mcp
ENV MESSAGES_DB_PATH=/data/store/messages.db \
    WHATSAPP_API_BASE_URL=http://bridge:8080/api \
    UV_NO_SYNC=1 \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000
CMD ["/app/.venv/bin/python", "/app/main.py"]
