# GitHub Secrets Configuration

This document lists all the secrets that need to be configured in GitHub repository settings.

## Required Secrets

### Yandex Cloud Container Registry
- **`YA_DOCKER_OAUTH`**: OAuth token for Yandex Cloud Container Registry
- **`YC_REGISTRY_ID`**: Your Yandex Cloud Container Registry ID

### Virtual Machine Deployment
- **`VM_HOST`**: IP address or hostname of your virtual machine
- **`VM_USERNAME`**: SSH username for VM access
- **`VM_SSH_KEY`**: Private SSH key for VM authentication (full key including headers)

### Database Configuration
- **`DB_PASSWORD`**: PostgreSQL database password
- **`DB_USER`**: PostgreSQL database username (default: postgres)
- **`DB_NAME`**: PostgreSQL database name (default: koppen_mvp)
- **`DB_HOST`**: Database host (for external databases, otherwise not used)

### Application Secrets
- **`JWT_SECRET_KEY`**: Secret key for JWT token generation (should be a strong random string)
- **`GROQ_API_KEY`**: API key for Groq AI service
- **`API_BASE_URL`**: Base URL for the API (e.g., `http://localhost:8000` or `https://api.example.com`)

### Airflow (Optional)
- **`AIRFLOW_FERNET_KEY`**: Fernet key for Airflow encryption (generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- **`AIRFLOW_SECRET_KEY`**: Secret key for Airflow webserver

## How to Add Secrets to GitHub

1. Go to your GitHub repository
2. Navigate to **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Add each secret with the exact name listed above
5. For environment-specific secrets, create environments (development, staging, production) and add secrets there

## Environment-Specific Secrets

You can configure secrets per environment:
- Go to **Settings** > **Environments**
- Create environments: `development`, `staging`, `production`
- Add environment-specific secrets to override repository-level secrets

## Security Notes

- Never commit secrets to the repository
- Rotate secrets regularly
- Use different secrets for each environment (development, staging, production)
- Ensure SSH keys have proper permissions (600)

