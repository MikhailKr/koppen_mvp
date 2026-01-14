# Debugging Backend Container Restart Loop

When the backend container shows "Restarting" status, it means it's crashing and Docker is trying to restart it.

## Quick Diagnosis

```bash
# Check backend container logs (use container NAME, not ID)
docker logs koppen-app

# Or see the last 100 lines
docker logs --tail 100 koppen-app

# Follow logs in real-time
docker logs -f koppen-app

# Check docker-compose logs (from the directory with docker-compose.prod.yml)
cd ~
docker-compose -f docker-compose.prod.yml logs koppen-app
```

## Common Causes and Solutions

### 1. Database Connection Issues

**Symptoms:** Logs show database connection errors

**Check:**
```bash
# Verify database is running and healthy
docker ps | grep postgres

# Check database logs
docker logs koppen-postgres

# Test database connection
docker exec koppen-postgres psql -U postgres -d koppen_mvp -c "SELECT 1;"
```

**Solution:** Make sure database container is healthy before backend starts. Check environment variables:
```bash
# Check if environment variables are set correctly
docker-compose -f ~/docker-compose.prod.yml config
```

### 2. Missing Environment Variables

**Symptoms:** Logs show errors about missing configuration

**Check:**
```bash
# Check what environment variables the container sees
docker exec koppen-app env | grep -E 'POSTGRES|JWT|GROQ'
```

**Solution:** Ensure all required secrets are set in GitHub Secrets and exported in the workflow.

### 3. Application Code Errors

**Symptoms:** Python errors, import errors, syntax errors

**Check logs:**
```bash
docker logs koppen-app 2>&1 | tail -50
```

**Common issues:**
- Missing dependencies
- Import errors
- Configuration errors
- Database migration errors

### 4. Port Already in Use

**Symptoms:** "Address already in use" errors

**Check:**
```bash
sudo ss -tlnp | grep 8000
```

**Solution:**
```bash
# Stop all containers
docker-compose -f ~/docker-compose.prod.yml down

# Check for processes using port 8000
sudo lsof -i :8000

# Start again
docker-compose -f ~/docker-compose.prod.yml up -d
```

### 5. Entrypoint Script Errors

**Symptoms:** Errors in `/entrypoint.sh`

**Check:**
```bash
# View the entrypoint script (if mounted)
docker exec koppen-app cat /entrypoint.sh

# Or check if entrypoint script exists
docker exec koppen-app ls -la /entrypoint.sh
```

## Step-by-Step Debugging

1. **Get the actual error:**
   ```bash
   docker logs koppen-app --tail 100
   ```

2. **Check container status:**
   ```bash
   docker inspect koppen-app | grep -A 10 State
   ```

3. **Check environment variables:**
   ```bash
   docker-compose -f ~/docker-compose.prod.yml config | grep -A 20 "koppen-app:"
   ```

4. **Try running container interactively:**
   ```bash
   # Stop the container
   docker stop koppen-app
   
   # Run with interactive shell to debug
   docker run -it --rm \
     --env-file <(docker-compose -f ~/docker-compose.prod.yml config | grep -A 50 "koppen-app:" | grep "environment:" -A 50) \
     --network koppen-network \
     cr.yandex/crpdcq8rd3suju9jjn8k/koppen-backend:latest \
     /bin/bash
   ```

5. **Check if database is accessible:**
   ```bash
   # From backend container (when it's running)
   docker exec koppen-app python -c "import asyncio; from app.core.database import engine; print('DB OK')"
   ```

## Quick Fixes

### Restart All Services
```bash
cd ~
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### View All Logs
```bash
cd ~
docker-compose -f docker-compose.prod.yml logs
```

### Check Service Health
```bash
docker-compose -f ~/docker-compose.prod.yml ps
```

