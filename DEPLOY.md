# Azure Container App Deployment

## Prerequisites
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed and logged in (`az login`)
- Docker installed and running

## 1. Build & Push to Azure Container Registry
```bash
az acr login --name ythelper
docker build -t youtube-study-helper .
docker tag youtube-study-helper ythelper.azurecr.io/youtube-study-helper:latest
docker push ythelper.azurecr.io/youtube-study-helper:latest
```

## 2. Update the Container App
```bash
az containerapp update \
  --name ythelper \
  --resource-group personal \
  --image ythelper.azurecr.io/youtube-study-helper:latest \
  --set-env-vars \
    SUPADATA_API_KEY=sd_ed... \
    OPENROUTER_API_KEY=sk-or-v1-... \
    OPENROUTER_BASE_URL=https://openrouter.ai/api/v1 \
    OPENROUTER_MODEL_NAME=xiaomi/mimo-v2.5 \
    OPENROUTER_EMBEDDING_MODEL_NAME=openai/text-embedding-3-small
```

Or set the env vars via **Azure Portal → Container App ythelper → Containers → Environment variables**.

> The Docker image does NOT contain `.env` (excluded via `.dockerignore`). All config must be set as environment variables.
