# Accessing Services on Your VM

After deployment, here's how to access your services.

## Service Ports

Based on `docker-compose.prod.yml`, the following ports are exposed:

- **Frontend (Streamlit)**: Port `8501`
- **Backend API (FastAPI)**: Port `8000`
- **Database (PostgreSQL)**: Port `5432` (only for direct database access)
- **Airflow**: Port `8080` (if enabled)

## Accessing Services

### Option 1: From Your Local Machine (Recommended)

You need your VM's **IP address** or **hostname**:

```bash
# Get your VM's IP address (if you don't know it)
# From your VM, run:
hostname -I
# or
curl ifconfig.me  # Public IP
```

Then access:

- **Frontend (Main Application)**:
  ```
  http://YOUR_VM_IP:8501
  ```
  Example: `http://192.168.1.100:8501`

- **Backend API**:
  ```
  http://YOUR_VM_IP:8000
  ```
  Example: `http://192.168.1.100:8000`

- **API Documentation (Swagger)**:
  ```
  http://YOUR_VM_IP:8000/docs
  ```
  Example: `http://192.168.1.100:8000/docs`

- **Airflow** (if enabled):
  ```
  http://YOUR_VM_IP:8080
  ```
  Example: `http://192.168.1.100:8080`
  - Username: `admin`
  - Password: `admin` (default, change in production!)

### Option 2: From the VM Itself (SSH)

If you're SSH'd into the VM, you can test locally:

```bash
# Test Backend API
curl http://localhost:8000/api/v1/health

# Test Frontend (should return HTML)
curl http://localhost:8501

# Check if services are running
docker ps
```

## Verify Services Are Running

SSH into your VM and check:

```bash
# Check all containers
docker ps

# You should see:
# - koppen-app (backend)
# - koppen-frontend (frontend)
# - koppen-postgres (database)
# - koppen-airflow-webserver (if Airflow enabled)
# - koppen-airflow-scheduler (if Airflow enabled)

# Check logs
docker-compose -f ~/docker-compose.prod.yml logs -f

# Check specific service logs
docker logs koppen-app
docker logs koppen-frontend
docker logs koppen-postgres
```

## Firewall Configuration

If you can't access services from outside the VM, you may need to open ports in the firewall:

### Ubuntu/Debian (UFW)

```bash
# Allow HTTP ports
sudo ufw allow 8000/tcp   # Backend API
sudo ufw allow 8501/tcp   # Frontend
sudo ufw allow 8080/tcp   # Airflow (if enabled)

# Check firewall status
sudo ufw status

# Enable firewall if not enabled
sudo ufw enable
```

### Yandex Cloud / Other Cloud Providers

Make sure your **security group** allows inbound traffic on:
- Port `8000` (Backend API)
- Port `8501` (Frontend)
- Port `8080` (Airflow, if enabled)

## Using Nginx (Optional)

If you have Nginx configured (via `nginx/nginx.conf`), you can:

1. Install Nginx on your VM:
   ```bash
   sudo apt-get update
   sudo apt-get install nginx
   ```

2. Copy the nginx config:
   ```bash
   sudo cp ~/koppen-nginx/nginx.conf /etc/nginx/sites-available/koppen
   sudo ln -s /etc/nginx/sites-available/koppen /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

3. Access via port 80:
   - Frontend: `http://YOUR_VM_IP/`
   - Backend API: `http://YOUR_VM_IP/api/`

## Troubleshooting

### Can't access services from outside

1. **Check containers are running:**
   ```bash
   docker ps
   ```

2. **Check ports are listening:**
   ```bash
   sudo netstat -tlnp | grep -E '8000|8501|8080'
   # or
   sudo ss -tlnp | grep -E '8000|8501|8080'
   ```

3. **Check firewall:**
   ```bash
   sudo ufw status
   ```

4. **Check VM security groups** (if using cloud provider)

5. **Test from VM itself:**
   ```bash
   curl http://localhost:8000/api/v1/health
   curl http://localhost:8501
   ```

### Services show as "unhealthy" or won't start

```bash
# Check logs
docker-compose -f ~/docker-compose.prod.yml logs

# Restart services
docker-compose -f ~/docker-compose.prod.yml restart

# Recreate containers
docker-compose -f ~/docker-compose.prod.yml up -d --force-recreate
```

### Database connection errors

```bash
# Check database is running
docker logs koppen-postgres

# Test database connection
docker exec koppen-postgres psql -U postgres -d koppen_mvp -c "SELECT 1;"
```

## Quick Access Checklist

- [ ] Services are running (`docker ps`)
- [ ] Firewall allows ports 8000, 8501 (and 8080 if using Airflow)
- [ ] Security group allows inbound traffic (if cloud VM)
- [ ] You know your VM's IP address
- [ ] Can access from browser: `http://YOUR_VM_IP:8501`

## Security Recommendations

1. **Change default passwords** (Airflow admin password)
2. **Use HTTPS** in production (set up SSL/TLS certificates)
3. **Restrict database port** (5432) - only allow from trusted IPs
4. **Use firewall rules** to limit access
5. **Set up authentication** for API access
6. **Keep services updated** regularly

