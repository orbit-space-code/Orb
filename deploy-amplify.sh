#!/bin/bash

# AWS Amplify Deployment Script for OrbitSpace
# App ID: d2hrq8nzx5xf6w
# Region: us-west-1
# Production URL: https://orbitspace.org
# Framework: Next.js - SSR

echo "🚀 Starting AWS Amplify deployment for OrbitSpace..."
echo "📍 App ID: d2hrq8nzx5xf6w"
echo "🌍 Region: us-west-1"
echo "🌐 Production URL: https://orbitspace.org"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Check if Amplify CLI is installed
if ! command -v amplify &> /dev/null; then
    echo "📦 Installing AWS Amplify CLI..."
    npm install -g @aws-amplify/cli
fi

# Initialize Amplify (if not already initialized)
if [ ! -d ".amplify" ]; then
    echo "🔧 Initializing Amplify project..."
    amplify init \
        --name orbitspace \
        --env production \
        --default-editor code \
        --app-id d2hrq8nzx5xf6w \
        --yes
fi

# Add backend API
echo "🔧 Adding backend API..."
amplify add api \
    --name orbitspace-api \
    --type REST \
    --runtime python3.11 \
    --handler lambda_handler.lambda_handler \
    --path / \
    --defaultAuthType AMAZON_COGNITO_USER_POOLS \
    --yes

# Add Lambda function
echo "🔧 Adding Lambda function..."
amplify add function \
    --name orbitspace-backend \
    --runtime python3.11 \
    --handler lambda_handler.lambda_handler \
    --timeout 300 \
    --memory 512 \
    --environment "PYTHON_ENV=production" \
    --yes

# Add storage (S3 bucket)
echo "🔧 Adding storage..."
amplify add storage \
    --name orbitspace-storage \
    --type S3 \
    --yes

# Add hosting (Next.js SSR)
echo "🔧 Adding Next.js SSR hosting..."
amplify add hosting \
    --type CLOUDFRONT_AND_S3 \
    --framework Next.js \
    --yes

# Push backend configuration
echo "🚀 Pushing backend configuration to AWS..."
amplify push --yes

# Deploy everything
echo "🚀 Deploying to AWS Amplify..."
amplify publish --yes

echo "✅ Deployment completed!"
echo ""
echo "📋 Deployment Summary:"
echo "📍 App ID: d2hrq8nzx5xf6w"
echo "🌍 Region: us-west-1"
echo "🌐 Production URL: https://orbitspace.org"
echo "📦 Framework: Next.js - SSR"
echo ""
echo "📋 Next steps:"
echo "1. Set up environment variables in AWS Amplify console:"
echo "   - DATABASE_URL"
echo "   - REDIS_URL"
echo "   - FASTAPI_SECRET_KEY"
echo "   - GITHUB_CLIENT_ID"
echo "   - GITHUB_CLIENT_SECRET"
echo "   - And other variables from amplify-env.template"
echo ""
echo "2. Configure custom domain in Amplify console"
echo "3. Set up CI/CD pipeline in Amplify console"
echo "4. Test the deployed application at https://orbitspace.org"
