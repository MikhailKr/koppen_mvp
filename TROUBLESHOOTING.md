# Troubleshooting Deployment Issues

## Error: "docker: command not found"

This error occurs when Docker is not installed on your VM or not in the PATH.

### Solution 1: Install Docker on Your VM

SSH into your VM and run:

```bash
# Update package list
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (to run without sudo)
sudo usermod -aG docker $USER

# Logout and login again, or run:
newgrp docker

# Verify Docker installation
docker --version
docker ps
```

### Solution 2: Install docker-compose

```bash
# Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

### Solution 3: Check Docker Service Status

```bash
# Check if Docker service is running
sudo systemctl status docker

# Start Docker service if not running
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker
```

### Solution 4: Verify PATH

Make sure Docker is in your PATH:

```bash
# Check Docker location
which docker
which docker-compose

# If not found, check if installed in different location
sudo find / -name docker 2>/dev/null | grep -v proc

# Add to PATH if needed (add to ~/.bashrc or ~/.profile)
export PATH=$PATH:/usr/local/bin
```

### Solution 5: Test SSH Connection

Make sure the GitHub Actions can execute commands properly:

```bash
# Test from your local machine
ssh -i ~/.ssh/your_key user@your-vm-host "docker --version"
```

If this works but GitHub Actions doesn't, check:
- SSH user has proper permissions
- SSH key is correctly configured
- User's shell is properly configured (bash, not sh)

### Quick Check Script

Run this on your VM to verify everything is set up:

```bash
#!/bin/bash
echo "Checking Docker installation..."
docker --version || echo "ERROR: Docker not found"
docker-compose --version || echo "ERROR: docker-compose not found"

echo "Checking Docker service..."
sudo systemctl status docker --no-pager || echo "ERROR: Docker service not running"

echo "Checking user groups..."
groups | grep docker || echo "WARNING: User not in docker group"

echo "Testing docker command..."
docker ps || echo "ERROR: Cannot run docker commands"
```

## Other Common Issues

### Error: Permission Denied

If you get permission errors:

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or run commands with sudo (not recommended for production)
sudo docker ps
```

### Error: Cannot Connect to Docker Daemon

```bash
# Start Docker service
sudo systemctl start docker

# Check Docker daemon status
sudo systemctl status docker
```

### Error: docker-compose not found

If docker-compose is installed but not found:

```bash
# Check if it's docker compose (v2) instead of docker-compose
docker compose version

# If using Docker Compose v2, update the workflow to use:
# docker compose (instead of docker-compose)
```

### Verify GitHub Actions Can Access Docker

After installing Docker on your VM, the GitHub Actions workflow should work. The workflow runs these commands:

1. `docker login` - Login to container registry
2. `docker pull` - Pull images
3. `docker-compose up -d` - Start services
4. `docker image prune -f` - Cleanup

All of these require Docker to be installed and accessible.

