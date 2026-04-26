FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /workspace

COPY . /workspace

RUN uv sync --project apps/worker --frozen

CMD ["uv", "run", "--project", "apps/worker", "python", "-m", "ai_desk_worker.runtime"]
