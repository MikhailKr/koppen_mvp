# Troubleshooting: Cannot Access Services via Browser

If containers are deployed but you can't access them via browser, follow these steps:

## Step 1: Verify Containers Are Running

SSH into your VM and check:

```bash
docker ps
```

You should see containers running:
- `koppen-app` (backend)
- `koppen-frontend` (frontend)
- `koppen-postgres` (database)

If containers are not running or show as "unhealthy", check logs:
```bash
docker-compose -f ~/docker-compose.prod.yml logs
docker logs koppen-app
docker logs koppen-frontend
```

## Step 2: Test Services Locally on VM

Test if services are responding on the VM itself:

```bash
# Test backend
curl http://localhost:8000/api/v1/health
# Should return: {"status":"ok"}

# Test frontend
curl http://localhost:8501
# Should return HTML content

# Check what ports are listening
sudo netstat -tlnp | grep -E '8000|8501'
# or
sudo ss -tlnp | grep -E '8000|8501'
```

**If this doesn't work**, the services aren't running correctly. Check logs above.

**If this works**, continue to Step 3 (firewall/network issue).

## Step 3: Check Firewall (UFW)

Most common issue! Check if firewall is blocking ports:

```bash
# Check firewall status
sudo ufw status

# If firewall is active, allow the ports:
sudo ufw allow 8000/tcp   # Backend API
sudo ufw allow 8501/tcp   # Frontend
sudo ufw allow 8080/tcp   # Airflow (if using)

# Verify rules were added
sudo ufw status numbered
```

## Step 4: Check Cloud Provider Security Groups

If using **Yandex Cloud**, **AWS**, **Azure**, **GCP**, or other cloud provider:

1. Go to your VM's security group settings
2. Add **inbound rules** for:
   - Port `8000` (TCP) - Backend API
   - Port `8501` (TCP) - Frontend
   - Port `8080` (TCP) - Airflow (if using)
3. Source: `0.0.0.0/0` (or your IP for security)
4. Save and wait a minute for rules to apply

## Step 5: Verify Correct IP Address

Make sure you're using the correct IP:

```bash
# Get private IP (if accessing from same network)
hostname -I

# Get public IP (if accessing from internet)
curl ifconfig.me
```

**Important:** 
- Use **private IP** if accessing from the same network/VPC
- Use **public IP** if accessing from the internet (and VM has public IP)

## Step 6: Test Network Connectivity

From your local machine (not the VM), test connectivity:

```bash
# Replace YOUR_VM_IP with actual IP
ping YOUR_VM_IP

# Test if ports are reachable
telnet YOUR_VM_IP 8501
# or
nc -zv YOUR_VM_IP 8501
nc -zv YOUR_VM_IP 8000

# Test HTTP connection
curl http://YOUR_VM_IP:8501
curl http://YOUR_VM_IP:8000/api/v1/health
```

If `ping` works but ports don't respond → firewall/security group issue
If `ping` doesn't work → network/routing issue

## Step 7: Check Service Binding

Verify services are binding to `0.0.0.0` (all interfaces), not just `localhost`:

```bash
# Check what services are listening on
sudo ss -tlnp | grep -E '8000|8501'

# Should show:
# LISTEN  0  ...  0.0.0.0:8000  ...  # Backend
# LISTEN  0  ...  0.0.0.0:8501  ...  # Frontend

# If it shows 127.0.0.1:8501 instead of 0.0.0.0:8501, 
# the service is only listening on localhost
```

## Step 8: Check Docker Port Mapping

Verify ports are correctly mapped:

```bash
docker ps

# Check port mapping column, should show:
# 0.0.0.0:8000->8000/tcp   # Backend
# 0.0.0.0:8501->8501/tcp   # Frontend
```

## Common Solutions

### Solution 1: Firewall is blocking (Most Common)

```bash
sudo ufw allow 8000/tcp
sudo ufw allow 8501/tcp
sudo ufw reload
```

### Solution 2: Cloud Security Group

Add inbound rules in your cloud provider's console for ports 8000 and 8501.

### Solution 3: Services not running

```bash
# Restart services
docker-compose -f ~/docker-compose.prod.yml restart

# Or recreate
docker-compose -f ~/docker-compose.prod.yml up -d
```

### Solution 4: Wrong IP address

```bash
# Make sure you're using the correct IP
# Private IP for same network, Public IP for internet access
hostname -I
curl ifconfig.me
```

### Solution 5: Services binding to wrong interface

Check docker-compose.prod.yml - ports should be mapped as `"8000:8000"` not `"127.0.0.1:8000:8000"`

## Quick Diagnostic Script

Run this on your VM to get a complete picture:

```bash
#!/bin/bash
echo "=== Container Status ==="
docker ps

echo -e "\n=== Services Listening ==="
sudo ss -tlnp | grep -E '8000|8501|8080'

echo -e "\n=== Firewall Status ==="
sudo ufw status

echo -e "\n=== IP Addresses ==="
echo "Private IP: $(hostname -I)"
echo "Public IP: $(curl -s ifconfig.me)"

echo -e "\n=== Testing Services Locally ==="
curl -s http://localhost:8000/api/v1/health && echo " - Backend OK" || echo " - Backend FAILED"
curl -s http://localhost:8501 | head -1 && echo " - Frontend OK" || echo " - Frontend FAILED"
```

Save as `check_services.sh`, make executable (`chmod +x check_services.sh`), and run it.

## Still Not Working?

1. **Check browser console** for any errors
2. **Try different browser** or incognito mode
3. **Check if VM has public IP** (if accessing from internet)
4. **Check VM network settings** (NAT, routing, etc.)
5. **Review container logs** for errors:
   ```bash
   docker-compose -f ~/docker-compose.prod.yml logs --tail=100
   ```

