# Troubleshooting Guide

## Portal Can't Connect to API (ERR_CONNECTION_REFUSED)

### Problem
The portal shows "Network Error" and console shows `ERR_CONNECTION_REFUSED` when trying to connect to the API.

### Common Causes

1. **Support-core service isn't running**
   ```bash
   docker-compose ps
   ```
   Check if `support-core` is running. If not:
   ```bash
   docker-compose up -d support-core
   ```

2. **Wrong API URL in .env file**
   
   If you're accessing the portal from a browser on a different machine than where Docker is running, `localhost:8001` won't work.
   
   **Solution:** Update `apps/portal/.env` to use the host's IP address or domain name:
   
   ```bash
   # If accessing from same machine
   NEXT_PUBLIC_API_URL=http://localhost:8001
   
   # If accessing from different machine (replace with your Docker host IP/domain)
   NEXT_PUBLIC_API_URL=http://vm-ai.home.lan:8001
   # or
   NEXT_PUBLIC_API_URL=http://192.168.1.100:8001
   ```

3. **Port not exposed correctly**
   
   Check that port 8001 is mapped in docker-compose.yml:
   ```yaml
   support-core:
     ports:
       - "8001:8000"  # External:Internal
   ```

### Quick Fix Steps

1. **Check if support-core is running:**
   ```bash
   docker-compose ps support-core
   docker-compose logs support-core
   ```

2. **Update portal .env file:**
   ```bash
   cd apps/portal
   nano .env
   ```
   
   Set `NEXT_PUBLIC_API_URL` to the correct address:
   - Same machine: `http://localhost:8001`
   - Different machine: `http://YOUR_HOST_IP:8001` or `http://YOUR_DOMAIN:8001`

3. **Restart portal:**
   ```bash
   docker-compose restart portal
   ```

4. **Test API directly:**
   ```bash
   curl http://localhost:8001/health
   # or from browser: http://YOUR_HOST:8001/health
   ```

### For Production

In production, you should use:
- A reverse proxy (nginx, Traefik) with proper domain names
- HTTPS endpoints
- Example: `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`

