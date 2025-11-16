# AWS Amplify Deployment Guide for OrbitSpace

This guide covers deploying OrbitSpace to AWS Amplify with both frontend (Next.js) and backend (FastAPI) components.

## 📋 Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Node.js** (v18 or later)
4. **Python 3.11+**
5. **Amplify CLI**: `npm install -g @aws-amplify/cli`

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd Orb-main
npm install
pip install -r requirements.txt
```

### 2. Initialize Amplify

```bash
# Initialize Amplify project
amplify init --name orbitspace --env production --yes

# Add backend API
amplify add api --name orbitspace-api --type REST --runtime python3.11 --handler lambda_handler.lambda_handler --yes

# Add Lambda function
amplify add function --name orbitspace-backend --runtime python3.11 --handler lambda_handler.lambda_handler --yes

# Add hosting
amplify add hosting --type CLOUDFRONT --yes
```

### 3. Deploy

```bash
# Push configuration and deploy
amplify push --yes
amplify publish --yes
```

## 🔧 Environment Variables

Set these in the AWS Amplify console (Backend > Environment variables):

### Required Variables
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection URL
- `FASTAPI_SECRET_KEY` - FastAPI secret key
- `GITHUB_CLIENT_ID` - GitHub OAuth app client ID
- `GITHUB_CLIENT_SECRET` - GitHub OAuth app secret
- `GITHUB_APP_ID` - GitHub App ID
- `GITHUB_APP_PRIVATE_KEY` - GitHub App private key

### Optional Variables
- `ANTHROPIC_API_KEY` - Claude API key
- `AWS_REGION` - AWS region (default: us-east-1)
- `PYTHON_ENV` - Python environment (production)
- `NODE_ENV` - Node environment (production)

## 📁 Project Structure

```
Orb-main/
├── amplify.yml                 # Amplify CI/CD configuration
├── amplify/                    # Amplify configuration files
│   ├── backend.json           # Backend configuration
│   └── frontend.json          # Frontend configuration
├── amplify-env.template       # Environment variables template
├── deploy-amplify.sh          # Deployment script
├── lambda_handler.py          # AWS Lambda handler
├── main.py                    # FastAPI application
├── requirements.txt           # Python dependencies
└── package.json              # Node.js dependencies
```

## 🔍 Architecture

### Backend (FastAPI + Lambda)
- **Runtime**: Python 3.11
- **Framework**: FastAPI with Mangum for Lambda compatibility
- **Handler**: `lambda_handler.lambda_handler`
- **Memory**: 512 MB
- **Timeout**: 300 seconds

### Frontend (Next.js)
- **Framework**: Next.js 13+ with App Router
- **Build**: Static generation with ISR
- **Hosting**: Amplify Hosting with CloudFront CDN

### Database & Storage
- **Database**: PostgreSQL (external provider)
- **Cache**: Redis (external provider)
- **Storage**: S3 bucket for file storage

## 🚦 Deployment Process

1. **Code Push** → GitHub repository
2. **Amplify Build** → CI/CD pipeline runs
3. **Backend Build** → Python dependencies, tests
4. **Frontend Build** → Next.js build process
5. **Deployment** → Lambda functions + CloudFront
6. **Environment Variables** → Applied from Amplify console

## 🧪 Testing

```bash
# Test backend locally
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Test frontend locally
npm run dev

# Run tests
npm test
python -m pytest tests/ --cov=src
```

## 🔐 Security

- **CORS**: Configured for Amplify domains
- **Authentication**: GitHub OAuth + NextAuth.js
- **Environment Variables**: Stored securely in Amplify
- **API Security**: HTTP Bearer tokens, rate limiting

## 📊 Monitoring

- **AWS CloudWatch**: Logs and metrics
- **Amplify Console**: Build logs and deployment status
- **Error Tracking**: Sentry integration (if configured)

## 🔄 CI/CD

The `amplify.yml` file defines the CI/CD pipeline:

- **Pre-build**: Install dependencies
- **Build**: Run tests, build applications
- **Post-build**: Deployment preparation
- **Artifacts**: Frontend build output
- **Cache**: Dependencies for faster builds

## 🛠 Troubleshooting

### Common Issues

1. **Environment Variables Not Loading**
   - Ensure all required variables are set in Amplify console
   - Check `amplify-env.template` for reference

2. **Build Failures**
   - Check build logs in Amplify console
   - Verify all dependencies are in `requirements.txt` and `package.json`

3. **CORS Errors**
   - Update `FASTAPI_CORS_ORIGINS` in environment variables
   - Include your Amplify domain

4. **Lambda Timeouts**
   - Increase timeout in Lambda configuration
   - Optimize code for faster execution

### Debug Commands

```bash
# Check Amplify status
amplify status

# View logs
amplify logs

# Test locally
amplify mock function orbitspace-backend
```

## 📞 Support

For issues with:
- **AWS Amplify**: AWS Support + Amplify documentation
- **Application Code**: GitHub Issues
- **Deployment**: Check AWS CloudWatch logs

## 🔄 Updates

To update the deployment:

1. Push code changes to GitHub
2. Amplify automatically triggers new build
3. Monitor build in Amplify console
4. Test deployed application

## 📚 Additional Resources

- [AWS Amplify Documentation](https://docs.aws.amazon.com/amplify/)
- [FastAPI + AWS Lambda Guide](https://fastapi.tiangolo.com/deployment/aws-lambda/)
- [Next.js on Amplify](https://docs.aws.amazon.com/amplify/hosting/)
