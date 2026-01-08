# GitHub Actions CI/CD Pipeline

This repository uses GitHub Actions for continuous integration and deployment.

## Workflow Overview

The CI/CD pipeline consists of three main stages:

1. **Test and Lint** - Runs code quality checks and tests
2. **Build and Push** - Builds Docker images and pushes to Yandex Cloud Container Registry
3. **Deploy** - Deploys the application to a virtual machine

## Workflow Name

The workflow is named **CI/CD** as specified.

## Triggering the Workflow

The workflow is triggered on:
- Push to `main` branch
- Pull requests to `main` branch
- Manual dispatch via GitHub Actions UI with options:
  - **Version**: Tag for the Docker image (default: `latest`)
  - **Environment**: Target environment (development, staging, production)

## Manual Deployment

To manually trigger a deployment:

1. Go to **Actions** tab in GitHub
2. Select **CI/CD** workflow
3. Click **Run workflow**
4. Choose:
   - Branch: `main`
   - Version: Image tag (e.g., `v1.0.0` or `latest`)
   - Environment: `development`, `staging`, or `production`
5. Click **Run workflow**

## Environments

The workflow supports three environments:
- **development** - Development environment (default)
- **staging** - Staging environment
- **production** - Production environment

Each environment can have its own secrets configured in GitHub repository settings.

## Docker Images

The pipeline builds two Docker images:
- `koppen-backend` - FastAPI backend application
- `koppen-frontend` - Streamlit frontend application

Images are tagged with:
- The specified version (or `latest` by default)
- The Git commit SHA for traceability

## Secrets Configuration

See [SECRETS.md](./SECRETS.md) for a complete list of required secrets.

## Deployment Process

1. **Test and Lint**: Runs ruff linting and pytest tests
2. **Build**: Builds backend and frontend Docker images
3. **Push**: Pushes images to Yandex Cloud Container Registry
4. **Deploy**: 
   - Connects to VM via SSH
   - Copies docker-compose.prod.yml and nginx configs
   - Pulls latest images
   - Stops old containers
   - Starts new containers with updated images
   - Cleans up old Docker images

## Troubleshooting

### Workflow fails at test stage
- Check that all dependencies are correctly specified in `pyproject.toml`
- Ensure tests are in the `tests/` directory
- Review linting errors and fix code style issues

### Build fails
- Verify Dockerfile syntax
- Check that all required files are present in the repository
- Ensure build context is correct

### Deployment fails
- Verify SSH credentials are correct
- Check that VM is accessible
- Ensure Docker and docker-compose are installed on VM
- Verify all required secrets are set

### Containers don't start
- Check docker-compose.prod.yml syntax
- Verify environment variables are set correctly
- Review container logs: `docker-compose -f ~/docker-compose.prod.yml logs`

