# VM Deployment - First Time Setup Guide

This guide explains how to deploy Koppen MVP on a virtual machine for the first time.

## Database Setup Options

You have **two options** for the database when deploying on your VM:

### Option 1: Use PostgreSQL in Docker (Recommended for First Deployment) ✅

This is the **easiest option** and what `docker-compose.prod.yml` is configured for by default.

**Advantages:**
- No need to install PostgreSQL separately
- Database is managed by Docker
- Data persists in Docker volumes
- Easy to backup and restore
- Works out of the box

**Setup:**
1. The database will be created automatically when you run `docker-compose.prod.yml`
2. The database runs in a container named `koppen-postgres`
3. Data is stored in a Docker volume named `postgres_data`

**Environment Variables to Set (on VM or in GitHub Secrets):**
```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password-here
POSTGRES_DB=koppen_mvp
```

The `docker-compose.prod.yml` file handles:
- Creating the PostgreSQL container
- Setting up the database
- Creating the Airflow database
- Health checks
- Network configuration

### Option 2: Use External PostgreSQL (Advanced)

If you want to use an existing PostgreSQL server or a managed database service:

**Steps:**
1. Install PostgreSQL on your VM or use a managed service
2. Create a database:
   ```sql
   CREATE DATABASE koppen_mvp;
   CREATE DATABASE airflow;  -- For Airflow
   ```
3. Update `docker-compose.prod.yml` to point to external database:
   - Change `POSTGRES_HOST` from `db` to your database host
   - Update connection strings
   - Remove or comment out the `db` service

**Not recommended for first deployment** - Use Option 1 instead.

## First-Time Deployment Steps

### 1. Prepare Your VM

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER
```

### 2. Configure GitHub Secrets

Go to GitHub repository **Settings** > **Secrets and variables** > **Actions** and add:

**Required for database (Option 1 - Docker PostgreSQL):**
- `DB_PASSWORD` - Choose a strong password for PostgreSQL
- `DB_USER` - Usually `postgres` (default)
- `DB_NAME` - Usually `koppen_mvp` (default)

**Other required secrets:**
- `YA_DOCKER_OAUTH` - Yandex Cloud OAuth token
- `YC_REGISTRY_ID` - Your Container Registry ID
- `VM_HOST` - Your VM IP address
- `VM_USERNAME` - SSH username
- `VM_SSH_KEY` - SSH private key
- `JWT_SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `GROQ_API_KEY` - Your Groq API key

### 3. Generate Secure Passwords

```bash
# Generate JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate database password
openssl rand -base64 32

# Generate Airflow Fernet key (optional)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. Deploy

The GitHub Actions workflow will:
1. Build Docker images
2. Push to Yandex Cloud Container Registry
3. SSH to your VM
4. Pull images
5. Run `docker-compose.prod.yml` with environment variables from secrets

### 5. Manual Deployment (Alternative)

If you prefer to deploy manually:

```bash
# On your VM, create a .env file
cat > .env << EOF
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password-here
POSTGRES_DB=koppen_mvp
JWT_SECRET_KEY=your-jwt-secret-here
GROQ_API_KEY=your-groq-key-here
YC_REGISTRY_ID=your-registry-id
IMAGE_VERSION=latest
EOF

# Login to container registry
echo "YOUR_OAUTH_TOKEN" | docker login --username oauth --password-stdin cr.yandex

# Copy docker-compose.prod.yml to VM
# Then run:
docker-compose -f docker-compose.prod.yml --env-file .env up -d
```

## Database Migration

The application will automatically run database migrations on startup (Alembic migrations).

To check migration status:
```bash
docker exec koppen-app alembic current
```

To run migrations manually:
```bash
docker exec koppen-app alembic upgrade head
```

## Verify Deployment

1. Check containers are running:
   ```bash
   docker ps
   ```

2. Check logs:
   ```bash
   docker logs koppen-app
   docker logs koppen-frontend
   docker logs koppen-postgres
   ```

3. Access services:
   - Frontend: `http://your-vm-ip:8501`
   - Backend API: `http://your-vm-ip:8000`
   - Airflow: `http://your-vm-ip:8080` (if configured)

## Troubleshooting

### Database Connection Issues

If the app can't connect to the database:

1. Check database container is running:
   ```bash
   docker ps | grep postgres
   ```

2. Check database logs:
   ```bash
   docker logs koppen-postgres
   ```

3. Test connection from app container:
   ```bash
   docker exec koppen-app python -c "from app.core.config import settings; print(settings.database_url)"
   ```

### First-Time Database Setup

The database will be initialized automatically when the PostgreSQL container starts for the first time. The `init-airflow-db.sql` script creates the Airflow database.

If you need to reset the database:
```bash
# WARNING: This will delete all data!
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

## Backup Database

```bash
# Backup
docker exec koppen-postgres pg_dump -U postgres koppen_mvp > backup.sql

# Restore
docker exec -i koppen-postgres psql -U postgres koppen_mvp < backup.sql
```

