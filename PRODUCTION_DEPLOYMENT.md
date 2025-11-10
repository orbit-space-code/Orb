# Production Deployment Guide

Complete guide for deploying Orbitspace Compyle to production environments.

## **Table of Contents**

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Database Migration](#database-migration)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup Strategy](#backup-strategy)
9. [Scaling Considerations](#scaling-considerations)
10. [Troubleshooting](#troubleshooting)

---

## **Prerequisites**

### **Required Services:**
- ✅ **PostgreSQL 15+** (managed or self-hosted)
- ✅ **Redis 7+** (managed or self-hosted)
- ✅ **Domain name** with DNS configured
- ✅ **SSL certificate** (Let's Encrypt recommended)
- ✅ **GitHub App** configured for production domain

### **Required Credentials:**
- Anthropic API key (production tier)
- GitHub App credentials (Client ID, Secret, Private Key)
- Database connection string
- Redis connection string

### **Recommended Infrastructure:**
- **CPU:** 4+ cores per service
- **Memory:** 8GB+ RAM per service
- **Storage:** 100GB+ SSD (for workspaces)
- **Network:** 1Gbps+ bandwidth

---

## **Environment Setup**

### **1. Production Environment Variables**

Create `.env.production`:

```bash
# ========================================
# PRODUCTION ENVIRONMENT VARIABLES
# ========================================

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-...
RESEARCH_AGENT_MODEL=claude-sonnet-4-20250514
PLANNING_AGENT_MODEL=claude-sonnet-4-20250514
IMPLEMENTATION_AGENT_MODEL=claude-haiku-4-20250514

# Database (use managed PostgreSQL for production)
DATABASE_URL=postgresql://user:pass@prod-postgres.example.com:5432/compyle_prod?sslmode=require

# Redis (use managed Redis for production)
REDIS_URL=redis://prod-redis.example.com:6379
REDIS_PASSWORD=your-secure-redis-password

# GitHub App
GITHUB_CLIENT_ID=Iv1.abc123def456
GITHUB_CLIENT_SECRET=1234567890abcdef1234567890abcdef12345678
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_PATH=/app/secrets/github-app-key.pem

# NextAuth
NEXTAUTH_SECRET=<64-char-random-string>
NEXTAUTH_URL=https://yourdomain.com

# FastAPI
FASTAPI_URL=https://api.yourdomain.com
NEXTJS_API_URL=https://yourdomain.com

# Workspace Configuration
WORKSPACE_ROOT=/mnt/workspaces
MAX_WORKSPACE_SIZE_GB=50
WORKSPACE_RETENTION_DAYS=30

# Git Configuration
GIT_BOT_NAME=Compyle Bot
GIT_BOT_EMAIL=bot@compyle.dev

# Security
ALLOWED_BASH_COMMANDS=ls,cat,grep,git,npm,python,node,pytest,jest,npx
MAX_AGENT_ITERATIONS=50
AGENT_TIMEOUT_SECONDS=600

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=https://...@sentry.io/...  # Optional

# CORS (if frontend on different domain)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### **2. Generate Secrets**

```bash
# Generate NEXTAUTH_SECRET
openssl rand -base64 64

# Generate Redis password
openssl rand -base64 32

# Generate JWT secret (if needed)
openssl rand -hex 32
```

---

## **Docker Deployment**

### **Option 1: Docker Compose (Simple)**

**1. Clone and configure:**

```bash
git clone https://github.com/yourorg/orbitspace-compyle.git
cd orbitspace-compyle

# Copy environment files
cp .env.example .env.production

# Edit with production values
nano .env.production
```

**2. Create production docker-compose:**

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # Use external managed services for production
  # postgres and redis should be managed services

  fastapi:
    build:
      context: .
      dockerfile: Dockerfile.fastapi
    image: yourregistry.com/compyle-fastapi:latest
    ports:
      - "127.0.0.1:8000:8000"  # Only expose to localhost
    environment:
      - REDIS_URL=${REDIS_URL}
      - DATABASE_URL=${DATABASE_URL}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - WORKSPACE_ROOT=/workspaces
    volumes:
      - /mnt/workspaces:/workspaces
      - /etc/secrets/github-app-key.pem:/app/secrets/github-app-key.pem:ro
    restart: always
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

  nextjs:
    build:
      context: .
      dockerfile: Dockerfile.nextjs
    image: yourregistry.com/compyle-nextjs:latest
    ports:
      - "127.0.0.1:3000:3000"  # Only expose to localhost
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - FASTAPI_URL=http://fastapi:8000
      - GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID}
      - GITHUB_CLIENT_SECRET=${GITHUB_CLIENT_SECRET}
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
      - NEXTAUTH_URL=${NEXTAUTH_URL}
      - NODE_ENV=production
    depends_on:
      - fastapi
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000/api/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - /var/www/certbot:/var/www/certbot:ro
    depends_on:
      - nextjs
      - fastapi
    restart: always
```

**3. Create nginx.conf:**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream nextjs {
        server nextjs:3000;
    }

    upstream fastapi {
        server fastapi:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;
    limit_req_zone $binary_remote_addr zone=app_limit:10m rate=100r/m;

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

        # SSL configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Frontend (Next.js)
        location / {
            limit_req zone=app_limit burst=20 nodelay;
            proxy_pass http://nextjs;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }

        # Backend API (FastAPI)
        location /api/agents/ {
            limit_req zone=api_limit burst=10 nodelay;
            proxy_pass http://fastapi/agents/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Longer timeout for AI operations
            proxy_connect_timeout 600s;
            proxy_send_timeout 600s;
            proxy_read_timeout 600s;
        }

        # SSE streaming endpoint
        location /api/stream/ {
            proxy_pass http://fastapi/stream/;
            proxy_http_version 1.1;
            proxy_set_header Connection '';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_buffering off;
            proxy_cache off;
            chunked_transfer_encoding on;
        }
    }
}
```

**4. Deploy:**

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

---

## **Kubernetes Deployment**

### **1. Create Namespace**

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: compyle-prod
```

### **2. Create Secrets**

```bash
# Create secret for environment variables
kubectl create secret generic compyle-secrets \
  --from-literal=database-url="postgresql://..." \
  --from-literal=redis-url="redis://..." \
  --from-literal=anthropic-api-key="sk-ant-..." \
  --from-literal=github-client-secret="..." \
  --from-literal=nextauth-secret="..." \
  -n compyle-prod

# Create secret for GitHub App private key
kubectl create secret generic github-app-key \
  --from-file=github-app-key.pem \
  -n compyle-prod
```

### **3. FastAPI Deployment**

```yaml
# fastapi-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compyle-fastapi
  namespace: compyle-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: compyle-fastapi
  template:
    metadata:
      labels:
        app: compyle-fastapi
    spec:
      containers:
      - name: fastapi
        image: yourregistry.com/compyle-fastapi:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: compyle-secrets
              key: anthropic-api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: compyle-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: compyle-secrets
              key: redis-url
        - name: WORKSPACE_ROOT
          value: "/workspaces"
        volumeMounts:
        - name: workspaces
          mountPath: /workspaces
        - name: github-key
          mountPath: /app/secrets
          readOnly: true
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 40
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 20
          periodSeconds: 10
      volumes:
      - name: workspaces
        persistentVolumeClaim:
          claimName: workspaces-pvc
      - name: github-key
        secret:
          secretName: github-app-key
---
apiVersion: v1
kind: Service
metadata:
  name: compyle-fastapi-svc
  namespace: compyle-prod
spec:
  selector:
    app: compyle-fastapi
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### **4. Next.js Deployment**

```yaml
# nextjs-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compyle-nextjs
  namespace: compyle-prod
spec:
  replicas: 2
  selector:
    matchLabels:
      app: compyle-nextjs
  template:
    metadata:
      labels:
        app: compyle-nextjs
    spec:
      containers:
      - name: nextjs
        image: yourregistry.com/compyle-nextjs:latest
        ports:
        - containerPort: 3000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: compyle-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: compyle-secrets
              key: redis-url
        - name: FASTAPI_URL
          value: "http://compyle-fastapi-svc:8000"
        - name: GITHUB_CLIENT_ID
          value: "Iv1.abc123"
        - name: GITHUB_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: compyle-secrets
              key: github-client-secret
        - name: NEXTAUTH_SECRET
          valueFrom:
            secretKeyRef:
              name: compyle-secrets
              key: nextauth-secret
        - name: NEXTAUTH_URL
          value: "https://yourdomain.com"
        - name: NODE_ENV
          value: "production"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: compyle-nextjs-svc
  namespace: compyle-prod
spec:
  selector:
    app: compyle-nextjs
  ports:
  - port: 3000
    targetPort: 3000
  type: ClusterIP
```

### **5. Persistent Volume for Workspaces**

```yaml
# workspaces-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: workspaces-pvc
  namespace: compyle-prod
spec:
  accessModes:
    - ReadWriteMany  # Required for multiple FastAPI pods
  resources:
    requests:
      storage: 500Gi
  storageClassName: fast-ssd  # Use your cluster's SSD storage class
```

### **6. Ingress**

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: compyle-ingress
  namespace: compyle-prod
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "60"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - yourdomain.com
    secretName: compyle-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /api/agents
        pathType: Prefix
        backend:
          service:
            name: compyle-fastapi-svc
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: compyle-nextjs-svc
            port:
              number: 3000
```

### **7. Deploy to Kubernetes**

```bash
kubectl apply -f namespace.yaml
kubectl apply -f workspaces-pvc.yaml
kubectl apply -f fastapi-deployment.yaml
kubectl apply -f nextjs-deployment.yaml
kubectl apply -f ingress.yaml

# Check status
kubectl get pods -n compyle-prod
kubectl logs -f deployment/compyle-fastapi -n compyle-prod
```

---

## **Database Migration**

### **Run Prisma Migrations**

```bash
# On first deployment
npx prisma migrate deploy

# For updates
npx prisma migrate deploy --schema=./prisma/schema.prisma
```

### **Backup Before Migration**

```bash
# PostgreSQL backup
pg_dump -h prod-postgres.example.com -U user -d compyle_prod > backup_$(date +%Y%m%d).sql

# Restore if needed
psql -h prod-postgres.example.com -U user -d compyle_prod < backup_20250101.sql
```

---

## **Monitoring & Logging**

### **1. Structured Logging**

Already configured in `src/utils/logger.py`. Logs are JSON-formatted for easy parsing.

### **2. Add Sentry (Error Tracking)**

```bash
npm install @sentry/nextjs
pip install sentry-sdk
```

Configure in Next.js:

```javascript
// sentry.client.config.js
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
});
```

Configure in FastAPI:

```python
# src/main.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment="production",
    traces_sample_rate=0.1,
)
```

### **3. Prometheus Metrics** (Optional)

Add metrics endpoint to FastAPI:

```python
from prometheus_client import Counter, Histogram, generate_latest

agent_executions = Counter('agent_executions_total', 'Total agent executions')
agent_duration = Histogram('agent_duration_seconds', 'Agent execution duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## **Backup Strategy**

### **1. Database Backups**

```bash
# Daily automated backup script
#!/bin/bash
BACKUP_DIR=/backups/postgres
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h prod-postgres.example.com -U user compyle_prod | gzip > $BACKUP_DIR/compyle_$DATE.sql.gz

# Retain last 7 days
find $BACKUP_DIR -name "compyle_*.sql.gz" -mtime +7 -delete
```

### **2. Workspace Backups**

```bash
# Weekly workspace backup
tar -czf /backups/workspaces_$(date +%Y%m%d).tar.gz /mnt/workspaces/

# Upload to S3 (optional)
aws s3 cp /backups/workspaces_*.tar.gz s3://compyle-backups/
```

### **3. Redis Snapshots**

Configure Redis for automatic snapshots in `redis.conf`:

```
save 900 1
save 300 10
save 60 10000
```

---

## **Scaling Considerations**

### **Horizontal Scaling**

1. **FastAPI:** Scale based on agent execution load
   ```bash
   kubectl scale deployment compyle-fastapi --replicas=5 -n compyle-prod
   ```

2. **Next.js:** Scale based on user traffic
   ```bash
   kubectl scale deployment compyle-nextjs --replicas=3 -n compyle-prod
   ```

### **Vertical Scaling**

- Increase CPU/RAM for complex agent tasks
- Use larger workspaces volume for concurrent projects

### **Database Connection Pooling**

Configure Prisma connection pool:

```env
DATABASE_URL="postgresql://user:pass@host:5432/db?connection_limit=20&pool_timeout=60"
```

---

## **Troubleshooting**

### **High Memory Usage**

**Problem:** FastAPI containers running out of memory

**Solution:**
- Increase memory limits in deployment
- Reduce MAX_AGENT_ITERATIONS
- Add agent execution timeout

### **Slow Agent Responses**

**Problem:** Agent executions timing out

**Solution:**
- Check Anthropic API rate limits
- Verify Redis connectivity
- Increase AGENT_TIMEOUT_SECONDS

### **Failed Workspace Clones**

**Problem:** Git clone failures

**Solution:**
- Verify GitHub App installation
- Check private key is correctly mounted
- Ensure workspace volume has enough space

### **Database Connection Errors**

**Problem:** Connection pool exhausted

**Solution:**
```env
DATABASE_URL="...?connection_limit=50&pool_timeout=120"
```

---

## **Security Checklist**

- [ ] All secrets stored in environment variables or secrets manager
- [ ] SSL/TLS enabled with valid certificates
- [ ] GitHub App private key never committed to Git
- [ ] Rate limiting configured on Nginx/Ingress
- [ ] Database connections use SSL (sslmode=require)
- [ ] CORS properly configured for production domain
- [ ] Security headers added to Nginx
- [ ] Docker containers run as non-root user
- [ ] Network policies restrict pod-to-pod communication
- [ ] Regular security updates applied to base images

---

**Production deployment complete! Monitor logs and metrics closely for the first 48 hours.**
