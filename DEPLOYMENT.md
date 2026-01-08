# Deployment Guide

This guide explains how to deploy the Koppen MVP application using GitHub Actions CI/CD pipeline.

## Prerequisites

1. **GitHub Repository**: Push your code to a GitHub repository
2. **Yandex Cloud Container Registry**: Set up a container registry in Yandex Cloud
3. **Virtual Machine**: A VM with Docker and docker-compose installed
4. **GitHub Secrets**: Configure all required secrets in GitHub repository settings

## Quick Start

### 1. Configure GitHub Secrets

Go to your repository **Settings** > **Secrets and variables** > **Actions** and add:

#### Yandex Cloud
- `YA_DOCKER_OAUTH` - OAuth token for Container Registry
- `YC_REGISTRY_ID` - Your Container Registry ID

#### VM Access
- `VM_HOST` - VM IP address or hostname
- `VM_USERNAME` - SSH username
- `VM_SSH_KEY` - Private SSH key (full key with headers)

#### Database
- `DB_PASSWORD` - PostgreSQL password
- `DB_USER` - PostgreSQL username (default: `postgres`)
- `DB_NAME` - Database name (default: `koppen_mvp`)

#### Application
- `JWT_SECRET_KEY` - Strong random string for JWT tokens
- `GROQ_API_KEY` - Groq API key for AI features
- `API_BASE_URL` - API base URL (e.g., `http://app:8000`)

See `.github/SECRETS.md` for complete list.

### 2. Set Up Environments (Optional)

Create environments in GitHub for different deployment stages:
1. Go to **Settings** > **Environments**
2. Create: `development`, `staging`, `production`
3. Add environment-specific secrets if needed

### 3. Prepare Your VM

On your virtual machine, ensure Docker and docker-compose are installed:

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

### 4. Deploy

#### Automatic Deployment
- Push to `main` branch → automatic deployment to `development` environment

#### Manual Deployment
1. Go to **Actions** tab
2. Select **CI/CD** workflow
3. Click **Run workflow**
4. Select:
   - Branch: `main`
   - Version: Image tag (e.g., `v1.0.0`)
   - Environment: `development`, `staging`, or `production`

## What Gets Deployed

The pipeline builds and deploys:

- **Backend**: FastAPI application (`koppen-backend`)
- **Frontend**: Streamlit application (`koppen-frontend`)
- **Database**: PostgreSQL 16
- **Airflow**: For scheduled tasks (optional)

## Files Deployed to VM

- `docker-compose.prod.yml` - Production docker-compose configuration
- `nginx/*` - Nginx configuration files (if present)

## Verification

After deployment, check:

```bash
# SSH into your VM
ssh user@your-vm

# Check running containers
docker-compose -f ~/docker-compose.prod.yml ps

# View logs
docker-compose -f ~/docker-compose.prod.yml logs -f app
docker-compose -f ~/docker-compose.prod.yml logs -f frontend

# Check if services are accessible
curl http://localhost:8000/api/v1/health  # Backend
curl http://localhost:8501  # Frontend
```

## Rollback

To rollback to a previous version:

1. Find the commit SHA of the version you want
2. Run workflow manually with that SHA as the version tag
3. Or manually pull the old image:

```bash
ssh user@your-vm
docker pull cr.yandex/YOUR_REGISTRY_ID/koppen-backend:COMMIT_SHA
docker pull cr.yandex/YOUR_REGISTRY_ID/koppen-frontend:COMMIT_SHA
# Edit docker-compose.prod.yml to use COMMIT_SHA
docker-compose -f ~/docker-compose.prod.yml up -d
```

## Troubleshooting

### Workflow fails at test stage
- Check `pyproject.toml` dependencies
- Review test output in Actions logs
- Fix linting errors: `ruff check .`

### Build fails
- Verify Dockerfiles are correct
- Check that all required files exist
- Review build logs in Actions

### Deployment fails
- Verify SSH credentials in secrets
- Check VM accessibility: `ssh user@vm-host`
- Ensure Docker is installed on VM
- Check deployment logs in Actions

### Containers don't start
- Check logs: `docker-compose -f ~/docker-compose.prod.yml logs`
- Verify environment variables are set
- Check database connectivity
- Ensure ports are available

## Security Best Practices

1. **Use strong secrets**: Generate secure random strings for JWT_SECRET_KEY
2. **Rotate secrets**: Change secrets regularly, especially after team changes
3. **Environment separation**: Use different secrets for dev/staging/prod
4. **SSH keys**: Use dedicated deployment keys with minimal permissions
5. **Database**: Use strong passwords, limit network access
6. **Monitor logs**: Regularly review application and access logs

## Support

For issues or questions:
1. Check `.github/README.md` for workflow details
2. Review `.github/SECRETS.md` for secrets configuration
3. Check GitHub Actions logs for detailed error messages

