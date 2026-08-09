FROM node:22-alpine AS ui-build

ARG NPM_CONFIG_STRICT_SSL=true

WORKDIR /workspace/ui
COPY ui/package.json ui/package-lock.json ./
RUN npm config set strict-ssl "${NPM_CONFIG_STRICT_SSL}" && npm ci
COPY ui/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ARG PIP_TRUSTED_HOST=""

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    APP_ENV=production

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app/ app/
COPY peopleops_mcp/ peopleops_mcp/
RUN PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST}" python -m pip install .

COPY policy_corpus/ policy_corpus/
COPY mock_data/ mock_data/
COPY scripts/build_rag_index.py scripts/smoke_deployment.py scripts/
RUN python scripts/build_rag_index.py --check
COPY --from=ui-build /workspace/ui/dist/ ui/dist/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import json, urllib.request; response=urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3); assert json.load(response)['status'] == 'ok'"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
