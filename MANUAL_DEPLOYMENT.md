# Manual Deployment Guide

If you need to deploy manually on your VM (instead of using GitHub Actions), follow this guide.

## Setup Environment Variables

You need to set environment variables before running docker-compose. You have two options:

### Option 1: Create a .env file (Recommended)

Create a `.env` file in the same directory as `docker-compose.prod.yml`:

```bash
# On your VM
nano ~/.env
```

Add these variables (replace with your actual values):

```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password-here
POSTGRES_DB=koppen_mvp
JWT_SECRET_KEY=your-jwt-secret-key-here
GROQ_API_KEY=your-groq-api-key-here
YC_REGISTRY_ID=your-registry-id-here
IMAGE_VERSION=latest
IMAGE_REGISTRY=cr.yandex
API_BASE_URL=http://app:8000
AIRFLOW_FERNET_KEY=your-fernet-key-if-using-airflow
AIRFLOW_SECRET_KEY=your-airflow-secret-key
```

Save the file (Ctrl+X, then Y, then Enter).

### Option 2: Export Variables

Export variables directly in your shell session:

```bash
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your-secure-password-here
export POSTGRES_DB=koppen_mvp
export JWT_SECRET_KEY=your-jwt-secret-key-here
export GROQ_API_KEY=your-groq-api-key-here
export YC_REGISTRY_ID=your-registry-id-here
export IMAGE_VERSION=latest
export IMAGE_REGISTRY=cr.yandex
export API_BASE_URL=http://app:8000
```

## Login to Container Registry

Before pulling images, you need to login:

```bash
# Get your OAuth token from Yandex Cloud
echo "YOUR_OAUTH_TOKEN" | docker login --username oauth --password-stdin cr.yandex
```

## Deploy with docker-compose

### Using docker-compose (v1)

```bash
cd ~
docker-compose -f docker-compose.prod.yml --env-file .env up -d
```

### Using docker compose (v2 - with space)

```bash
cd ~
docker compose -f docker-compose.prod.yml --env-file .env up -d
```

**Note:** If you're using Docker Compose v2, the command is `docker compose` (with a space), not `docker-compose` (with a hyphen).

## Check Which Version You Have

```bash
# Check docker-compose version
docker-compose --version

# Or check docker compose (v2)
docker compose version
```

If `docker compose version` works, you're using v2. If `docker-compose --version` works, you're using v1.

## Verify Deployment

```bash
# Check running containers
docker ps

# Check logs
docker-compose -f docker-compose.prod.yml logs
# or
docker compose -f docker-compose.prod.yml logs

# Check specific service logs
docker logs koppen-app
docker logs koppen-frontend
docker logs koppen-postgres
```

## Stop Services

```bash
docker-compose -f docker-compose.prod.yml down
# or
docker compose -f docker-compose.prod.yml down
```

## Update Services

```bash
# Pull latest images
docker pull cr.yandex/YOUR_REGISTRY_ID/koppen-backend:latest
docker pull cr.yandex/YOUR_REGISTRY_ID/koppen-frontend:latest

# Restart with new images
docker-compose -f docker-compose.prod.yml up -d
# or
docker compose -f docker-compose.prod.yml up -d
```

## Common Errors

### Error: "invalid reference format" or "double slash"

This means environment variables are not set correctly. Check:
- `.env` file exists and has all required variables
- Variables don't have empty values
- You're using `--env-file .env` flag

### Error: "unknown shorthand flag: 'f'"

If you see this error, you might be using `docker -f` instead of `docker-compose -f` or `docker compose -f`.

Make sure you're using:
- `docker-compose -f` (v1)
- `docker compose -f` (v2 with space)
- NOT `docker -f` (this is wrong)

### Error: "unauthorized: authentication required"

You need to login to the container registry first:
```bash
echo "YOUR_OAUTH_TOKEN" | docker login --username oauth --password-stdin cr.yandex
```

### Error: "Cannot connect to Docker daemon"

Docker service might not be running:
```bash
sudo systemctl start docker
sudo systemctl status docker
```

