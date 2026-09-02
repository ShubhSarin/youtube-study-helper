# Azure Container App Deployment

Push changes to GitHub, then run:

```bash
az acr login --name ythelper
docker build -t youtube-study-helper .
docker tag youtube-study-helper ythelper.azurecr.io/youtube-study-helper:latest
docker push ythelper.azurecr.io/youtube-study-helper:latest
az containerapp update \
  --name ythelper \
  --resource-group personal \
  --image ythelper.azurecr.io/youtube-study-helper:latest \
  --target-port 8000
```

> **Note:** the app now serves on port **8000** (FastAPI + React SPA) instead of 8501 (Streamlit). Use `--target-port 8000` on the first `containerapp update`; afterwards the ingress target port persists.

> Environment variables (`OPENROUTER_API_KEY`, `SUPADATA_API_KEY`, etc.) are already set on the container app — no need to pass `--set-env-vars` again unless adding new ones.
