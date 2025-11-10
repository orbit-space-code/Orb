/**
 * Security configuration and utilities for OrbitSpace
 */

import { NextRequest } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from './auth'

// Security headers for production
export const securityHeaders = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-XSS-Protection': '1; mode=block',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'Content-Security-Policy': [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self'",
    "connect-src 'self' https://api.anthropic.com https://api.openai.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'"
  ].join('; ')
}

// Rate limiting configuration
export const rateLimits = {
  api: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
  },
  auth: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 5 // limit each IP to 5 auth attempts per windowMs
  },
  analysis: {
    windowMs: 60 * 60 * 1000, // 1 hour
    max: 10 // limit each user to 10 analysis sessions per hour
  }
}

// Validate API secret for internal communication
export function validateInternalApiSecret(request: NextRequest): boolean {
  const providedSecret = request.headers.get('x-api-secret')
  const expectedSecret = process.env.NEXTJS_API_SECRET
  
  if (!providedSecret || !expectedSecret) {
    return false
  }
  
  return providedSecret === expectedSecret
}

// Validate user session and permissions
export async function validateUserSession(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    
    if (!session?.user?.id) {
      return { valid: false, error: 'Unauthorized' }
    }
    
    return { valid: true, user: session.user }
  } catch (error) {
    return { valid: false, error: 'Session validation failed' }
  }
}

// Sanitize user input
export function sanitizeInput(input: string): string {
  return input
    .replace(/[<>]/g, '') // Remove potential HTML tags
    .replace(/['"]/g, '') // Remove quotes
    .trim()
    .slice(0, 1000) // Limit length
}

// Validate file upload
export function validateFileUpload(file: File): { valid: boolean; error?: string } {
  const maxSize = 10 * 1024 * 1024 // 10MB
  const allowedTypes = [
    'application/zip',
    'application/x-tar',
    'application/gzip',
    'text/plain',
    'application/json'
  ]
  
  if (file.size > maxSize) {
    return { valid: false, error: 'File too large (max 10MB)' }
  }
  
  if (!allowedTypes.includes(file.type)) {
    return { valid: false, error: 'File type not allowed' }
  }
  
  return { valid: true }
}

// Generate secure random string
export function generateSecureToken(length: number = 32): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  
  return result
}

// Validate environment variables
export function validateEnvironment(): { valid: boolean; missing: string[] } {
  const required = [
    'NEXTAUTH_SECRET',
    'NEXTAUTH_URL',
    'DATABASE_URL',
    'ENCRYPTION_KEY',
    'GITHUB_CLIENT_ID',
    'GITHUB_CLIENT_SECRET'
  ]
  
  const missing = required.filter(key => !process.env[key])
  
  return {
    valid: missing.length === 0,
    missing
  }
}

// Security middleware for API routes
export function withSecurity(handler: Function) {
  return async (request: NextRequest, ...args: any[]) => {
    // Add security headers
    const response = await handler(request, ...args)
    
    if (response && typeof response.headers?.set === 'function') {
      Object.entries(securityHeaders).forEach(([key, value]) => {
        response.headers.set(key, value)
      })
    }
    
    return response
  }
}