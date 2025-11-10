# GitHub App Setup Guide

Complete guide to creating and configuring a GitHub App for Orbitspace Compyle.

## **Why We Need a GitHub App**

The GitHub App provides:
1. **OAuth Authentication** - Users sign in with GitHub
2. **Repository Access** - Clone private repositories
3. **Git Operations** - Create branches and commits as "Compyle Bot"
4. **API Access** - List user's repositories

---

## **Step 1: Create GitHub App**

### **1.1 Navigate to GitHub Settings**
```
https://github.com/settings/apps/new
```
Or:
1. Go to GitHub.com
2. Click your profile picture → Settings
3. Scroll down to "Developer settings"
4. Click "GitHub Apps" → "New GitHub App"

### **1.2 Fill in App Information**

**GitHub App name:** `Orbitspace Compyle` (or your preferred name)

**Homepage URL:** `http://localhost:3000` (development) or your production URL

**Callback URL:**
```
http://localhost:3000/api/auth/callback/github
```
For production, use your domain:
```
https://yourdomain.com/api/auth/callback/github
```

**Setup URL:** Leave blank

**Webhook:**
- ✅ Active: **NO** (uncheck this)
- We don't need webhooks for this application

**Permissions:**

Select "Repository permissions":
- **Contents:** Read and write
- **Pull requests:** Read and write
- **Metadata:** Read-only (automatically selected)

Select "Account permissions":
- None needed

**Where can this GitHub App be installed?**
- ✅ **Only on this account** (recommended for development)
- Or "Any account" for public deployment

### **1.3 Create the App**

Click **"Create GitHub App"**

---

## **Step 2: Generate Credentials**

### **2.1 Note Your App ID**

After creation, you'll see:
```
App ID: 123456
```
**Save this!** You'll need it for configuration.

### **2.2 Generate Client Secret**

1. Scroll down to "Client secrets"
2. Click **"Generate a new client secret"**
3. **Copy the secret immediately** (you won't see it again!)
4. Save it securely

### **2.3 Generate Private Key**

1. Scroll down to "Private keys"
2. Click **"Generate a private key"**
3. A `.pem` file will download
4. Save this file securely (e.g., `~/compyle-github-app.pem`)

**Important:** Keep this private key secure! Don't commit it to Git.

---

## **Step 3: Install the App**

### **3.1 Install to Your Account**

1. On the GitHub App page, click "Install App" (left sidebar)
2. Select your account or organization
3. Choose repository access:
   - **All repositories** (easiest for development)
   - OR **Only select repositories** (more secure)
4. Click **"Install"**

### **3.2 Note the Installation ID** (Optional)

After installing, the URL will look like:
```
https://github.com/settings/installations/12345678
```
The number `12345678` is your installation ID (not needed for basic setup).

---

## **Step 4: Configure Environment Variables**

### **4.1 Next.js Configuration (.env.local)**

Create or edit `.env.local`:

```bash
# GitHub OAuth App Credentials
GITHUB_CLIENT_ID="Iv1.abc123def456"
GITHUB_CLIENT_SECRET="1234567890abcdef1234567890abcdef12345678"

# GitHub App ID
GITHUB_APP_ID="123456"

# GitHub App Private Key
# Option 1: Inline (escape newlines)
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"

# Option 2: File path
GITHUB_APP_PRIVATE_KEY_PATH="/path/to/private-key.pem"

# NextAuth Configuration
NEXTAUTH_SECRET="your-random-secret-here"
NEXTAUTH_URL="http://localhost:3000"
```

**Get your GITHUB_CLIENT_ID:**
- On your GitHub App page, look for "Client ID"

### **4.2 Generate NEXTAUTH_SECRET**

```bash
openssl rand -base64 32
```

Copy the output and use it as `NEXTAUTH_SECRET`.

### **4.3 FastAPI Configuration (.env)**

Create or edit `.env`:

```bash
# GitHub App (same as Next.js)
GITHUB_APP_ID="123456"
GITHUB_APP_PRIVATE_KEY_PATH="/path/to/private-key.pem"

# Git Bot Identity
GIT_BOT_NAME="Compyle Bot"
GIT_BOT_EMAIL="bot@compyle.dev"
```

---

## **Step 5: Test the Setup**

### **5.1 Start the Application**

```bash
# Terminal 1: Start services
docker-compose up -d

# Terminal 2: Start Next.js
npm run dev

# Terminal 3: Start FastAPI
cd src && python -m uvicorn main:app --reload
```

### **5.2 Test OAuth Flow**

1. Open http://localhost:3000
2. Click "Sign in with GitHub"
3. You should be redirected to GitHub
4. Authorize the app
5. You should be redirected back to your app

**If successful:** You'll see your name/email in the dashboard!

### **5.3 Test Repository Access**

1. Create a new project
2. Select a repository
3. Check if repositories are listed

**If successful:** You should see your repositories in the dropdown!

---

## **Troubleshooting**

### **"Invalid client_id" Error**

**Problem:** GitHub says the client ID is invalid.

**Solution:**
1. Check `GITHUB_CLIENT_ID` in `.env.local` matches GitHub App page
2. Restart Next.js dev server
3. Clear browser cookies and try again

### **"Callback URL mismatch" Error**

**Problem:** GitHub redirects to wrong URL.

**Solution:**
1. In GitHub App settings, verify callback URL is:
   ```
   http://localhost:3000/api/auth/callback/github
   ```
2. Make sure `NEXTAUTH_URL` in `.env.local` is correct
3. Update and save

### **"Cannot clone repository" Error**

**Problem:** FastAPI can't clone private repositories.

**Solution:**
1. Verify GitHub App is installed to your account
2. Check "Contents" permission is set to "Read and write"
3. Verify private key is correctly loaded:
   ```bash
   cat /path/to/private-key.pem
   # Should show: -----BEGIN RSA PRIVATE KEY-----
   ```

### **"403 Forbidden" When Accessing Repositories**

**Problem:** App doesn't have permission.

**Solution:**
1. Go to https://github.com/settings/installations
2. Click "Configure" on your app
3. Ensure "Repository access" includes the repos you need
4. Save

### **NextAuth Error: "No secret provided"**

**Problem:** `NEXTAUTH_SECRET` is missing or invalid.

**Solution:**
```bash
# Generate a new secret
openssl rand -base64 32

# Add to .env.local
NEXTAUTH_SECRET="<generated-secret>"

# Restart Next.js
npm run dev
```

---

## **Production Configuration**

### **Update Callback URL**

1. Go to your GitHub App settings
2. Update "Callback URL" to production domain:
   ```
   https://yourdomain.com/api/auth/callback/github
   ```

### **Update Homepage URL**

```
https://yourdomain.com
```

### **Update Environment Variables**

```bash
# Production .env.local
NEXTAUTH_URL="https://yourdomain.com"
GITHUB_CLIENT_ID="<your-client-id>"
GITHUB_CLIENT_SECRET="<your-client-secret>"
```

### **Secure Private Key**

**Option 1: Environment Variable**
```bash
# Convert PEM to single line
GITHUB_APP_PRIVATE_KEY=$(cat private-key.pem | awk '{printf "%s\\n", $0}')
```

**Option 2: Secrets Manager**
- AWS Secrets Manager
- Azure Key Vault
- Google Cloud Secret Manager

**Option 3: Kubernetes Secret**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: github-app-key
type: Opaque
data:
  private-key.pem: <base64-encoded-key>
```

---

## **Security Best Practices**

### **✅ DO:**
- Keep private key secure and never commit to Git
- Use environment variables for all secrets
- Rotate secrets regularly
- Use HTTPS in production
- Enable rate limiting
- Monitor app usage via GitHub App dashboard

### **❌ DON'T:**
- Commit `.env` or `.env.local` files
- Share private key via email or chat
- Use the same secrets across environments
- Give "All repositories" access in production (use selective access)
- Expose client secret in client-side code

---

## **GitHub App Limits**

### **Rate Limits:**
- **5,000 requests/hour** per installation
- **15,000 requests/hour** per app

### **If You Hit Limits:**
1. Implement caching
2. Use conditional requests (ETags)
3. Request rate limit increase from GitHub

---

## **Useful Links**

- **GitHub App Settings:** https://github.com/settings/apps
- **Installed Apps:** https://github.com/settings/installations
- **GitHub Apps Documentation:** https://docs.github.com/en/apps
- **NextAuth GitHub Provider:** https://next-auth.js.org/providers/github

---

## **Quick Reference**

### **Environment Variables Needed:**

```bash
# Next.js (.env.local)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
NEXTAUTH_SECRET=
NEXTAUTH_URL=

# FastAPI (.env)
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY_PATH=
GIT_BOT_NAME=
GIT_BOT_EMAIL=
```

### **Permissions Required:**
- ✅ Repository Contents: Read & Write
- ✅ Pull Requests: Read & Write
- ✅ Metadata: Read-only

### **Callback URL Format:**
```
Development: http://localhost:3000/api/auth/callback/github
Production:  https://yourdomain.com/api/auth/callback/github
```

---

**Setup complete! Your GitHub App is ready.** 🎉
