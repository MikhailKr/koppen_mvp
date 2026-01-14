# Fix Database Hostname Resolution Issue

The backend container cannot resolve the hostname "db". This is a Docker network DNS issue.

## Debug Steps (Run on VM)

### Step 1: Check if containers are on the same network

```bash
# Check backend network
docker inspect koppen-app | grep -A 20 Networks

# Check database network
docker inspect koppen-postgres | grep -A 20 Networks

# Both should show "koppen-network" or similar
```

### Step 2: Test DNS resolution from backend container

```bash
# Try to resolve "db" from backend container
docker exec koppen-app nslookup db
# or
docker exec koppen-app ping -c 1 db
```

If this fails, the containers are not on the same network.

### Step 3: Check network exists and containers are connected

```bash
# List all networks
docker network ls

# Inspect the koppen network
docker network inspect koppen-network

# Should show both koppen-app and koppen-postgres containers
```

### Step 4: Full restart (Most Likely Fix)

The issue might be that containers were started separately. Stop everything and restart together:

```bash
cd ~

# Stop everything
docker-compose -f docker-compose.prod.yml down

# Remove the network (if it exists but is broken)
docker network rm koppen-network 2>/dev/null || true

# Start everything together (this creates the network properly)
docker-compose -f docker-compose.prod.yml up -d

# Wait for database to be healthy
sleep 10

# Check status
docker-compose -f docker-compose.prod.yml ps

# Check backend logs
docker logs koppen-app --tail 50
```

### Step 5: Verify network connectivity

After restart, verify:

```bash
# From backend container, test DNS
docker exec koppen-app nslookup db

# Should output something like:
# Name:   db
# Address: 172.xx.xx.xx

# Test connectivity
docker exec koppen-app ping -c 2 db
```

## Alternative: Use container name instead of service name

If DNS resolution still doesn't work, you could try using the container name instead. However, this shouldn't be necessary if docker-compose is working correctly.

## Check Docker Compose Version

Some older versions of docker-compose have network issues:

```bash
docker-compose --version
docker compose version
```

If using docker-compose v1, consider upgrading to v2 (docker compose with space).

## Nuclear Option: Recreate Everything

If nothing works:

```bash
cd ~

# Stop and remove everything
docker-compose -f docker-compose.prod.yml down -v

# Remove networks manually
docker network prune -f

# Start fresh
docker-compose -f docker-compose.prod.yml up -d
```

