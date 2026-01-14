# VM Environment Variables - Production Values

This document provides the environment variable values you need for VM deployment.

## Quick Setup: Use PostgreSQL in Docker (Recommended) ✅

For **first-time deployment**, use PostgreSQL in Docker. This is the simplest option.

### Environment Variables for Your VM

Create a `.env` file on your VM with these values, or set them as GitHub Secrets:

```bash
# ==================== Database Configuration ====================
# PostgreSQL runs in Docker container - these values are used by docker-compose.prod.yml
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<generate-a-strong-password>
POSTGRES_DB=koppen_mvp

# ==================== Application Secrets ====================
JWT_SECRET_KEY=<generate-a-strong-secret-key>
GROQ_API_KEY=<your-groq-api-key>

# ==================== Docker Registry ====================
YC_REGISTRY_ID=<your-yandex-registry-id>
IMAGE_REGISTRY=cr.yandex
IMAGE_VERSION=latest

# ==================== API Configuration ====================
API_BASE_URL=http://app:8000

# ==================== Airflow (Optional) ====================
AIRFLOW_FERNET_KEY=<generate-if-using-airflow>
AIRFLOW_SECRET_KEY=<generate-a-secret>
```

## How to Generate Secure Values

### 1. Generate Database Password
```bash
openssl rand -base64 32
```
**Example output:** `xK9mP2vQ8wL4nR7tY1zA5bC6dE9fG0hI3jK=`

### 2. Generate JWT Secret Key
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
**Example output:** `mK9xL2vP8wQ4nR7tY1zA5bC6dE9fG0hI3jK5mN8pQ1rS4tU7wX0zA2cD5fG=`

### 3. Generate Airflow Fernet Key (if using Airflow)
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
**Example output:** `xK9mP2vQ8wL4nR7tY1zA5bC6dE9fG0hI3jK5mN8pQ1rS4tU7wX0zA2cD5fG8hI=`

### 4. Generate Airflow Secret Key
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Complete Example .env File for VM

Here's a complete example with placeholder values - **replace with your actual generated values**:

```bash
# Database - PostgreSQL in Docker
POSTGRES_USER=postgres
POSTGRES_PASSWORD=CHANGE_THIS_TO_STRONG_PASSWORD
POSTGRES_DB=koppen_mvp

# Application
JWT_SECRET_KEY=CHANGE_THIS_TO_STRONG_SECRET_KEY
GROQ_API_KEY=gsk_YOUR_GROQ_API_KEY_HERE

# Docker Registry
YC_REGISTRY_ID=your-registry-id-here
IMAGE_REGISTRY=cr.yandex
IMAGE_VERSION=latest

# API
API_BASE_URL=http://app:8000

# Airflow (optional)
AIRFLOW_FERNET_KEY=
AIRFLOW_SECRET_KEY=CHANGE_THIS_IF_USING_AIRFLOW
```

## Option 1: Set as GitHub Secrets (Recommended)

1. Go to GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:
   - `DB_PASSWORD` = your generated database password
   - `DB_USER` = `postgres`
   - `DB_NAME` = `koppen_mvp`
   - `JWT_SECRET_KEY` = your generated JWT secret
   - `GROQ_API_KEY` = your Groq API key
   - `YC_REGISTRY_ID` = your Yandex Cloud registry ID
   - `YA_DOCKER_OAUTH` = your Yandex Cloud OAuth token
   - `VM_HOST` = your VM IP address
   - `VM_USERNAME` = SSH username
   - `VM_SSH_KEY` = your SSH private key

The GitHub Actions workflow will automatically pass these to docker-compose on your VM.

## Option 2: Set on VM Directly

If you prefer to set values directly on the VM:

1. **SSH into your VM**
2. **Create `.env` file** in the directory where you'll run docker-compose:
   ```bash
   nano .env
   ```
3. **Paste your environment variables** (use the example above)
4. **Save and exit** (Ctrl+X, then Y, then Enter)
5. **Set secure permissions**:
   ```bash
   chmod 600 .env
   ```

Then run docker-compose:
```bash
docker-compose -f docker-compose.prod.yml --env-file .env up -d
```

## Important Notes

### Database Host Configuration

When using PostgreSQL in Docker (recommended):
- **POSTGRES_HOST** = `db` (this is the Docker service name, NOT your VM_HOST)
- **POSTGRES_PORT** = `5432` (internal Docker network port)
- These are **already set** in `docker-compose.prod.yml` - you don't need to set them

**Important:** `POSTGRES_HOST` is different from `VM_HOST`:
- `POSTGRES_HOST` = `db` (Docker service name for container-to-container communication)
- `VM_HOST` = your VM's IP address (for SSH/deployment only, not for database)

The `docker-compose.prod.yml` file automatically:
- Creates the PostgreSQL container
- Sets up the database
- Connects the app to the database
- Creates Docker volumes for data persistence

### First-Time Database Setup

When you deploy for the first time:
1. The PostgreSQL container will start automatically
2. The database `koppen_mvp` will be created automatically
3. The Airflow database will be created automatically (via init script)
4. Alembic migrations will run automatically when the app starts

**You don't need to manually create the database!**

## Verify Your Setup

After deployment, verify everything is working:

```bash
# Check containers are running
docker ps

# Check database is accessible
docker exec koppen-postgres psql -U postgres -c "\l"

# Check app logs
docker logs koppen-app

# Check frontend logs
docker logs koppen-frontend
```

## Security Reminders

1. ✅ Never commit `.env` files to git (already in .gitignore)
2. ✅ Use strong, randomly generated passwords
3. ✅ Keep secrets secure - don't share them
4. ✅ Rotate secrets regularly in production
5. ✅ Use different values for development/staging/production

