#!/usr/bin/env node

/**
 * OrbitSpace Secret Generation Script
 * Generates cryptographically secure secrets for production deployment
 */

const crypto = require('crypto');

console.log('🔐 OrbitSpace Production Secrets Generator');
console.log('==========================================\n');

// Generate NextAuth Secret (128 characters hex)
const nextAuthSecret = crypto.randomBytes(64).toString('hex');
console.log('NextAuth Secret (NEXTAUTH_SECRET):');
console.log(nextAuthSecret);
console.log('');

// Generate FastAPI Secret Key (128 characters hex)
const fastApiSecret = crypto.randomBytes(64).toString('hex');
console.log('FastAPI Secret Key (FASTAPI_SECRET_KEY):');
console.log(fastApiSecret);
console.log('');

// Generate Internal API Secret (Base64 encoded)
const internalApiSecret = crypto.randomBytes(32).toString('base64');
console.log('Internal API Secret (NEXTJS_API_SECRET):');
console.log(internalApiSecret);
console.log('');

// Generate Encryption Key (64 characters hex)
const encryptionKey = crypto.randomBytes(32).toString('hex');
console.log('Encryption Key (ENCRYPTION_KEY):');
console.log(encryptionKey);
console.log('');

// Generate JWT Secret for additional security
const jwtSecret = crypto.randomBytes(32).toString('base64');
console.log('Additional JWT Secret (Optional):');
console.log(jwtSecret);
console.log('');

console.log('📋 Environment Variables for .env file:');
console.log('=====================================');
console.log(`NEXTAUTH_SECRET="${nextAuthSecret}"`);
console.log(`FASTAPI_SECRET_KEY="${fastApiSecret}"`);
console.log(`NEXTJS_API_SECRET="${internalApiSecret}"`);
console.log(`ENCRYPTION_KEY="${encryptionKey}"`);
console.log('');

console.log('⚠️  Security Notes:');
console.log('- Keep these secrets secure and never commit them to version control');
console.log('- Use different secrets for development, staging, and production');
console.log('- Rotate secrets regularly for enhanced security');
console.log('- Store secrets in environment variables or secure secret management');
console.log('');

console.log('✅ Secrets generated successfully!');
console.log('Copy the environment variables above to your .env file');