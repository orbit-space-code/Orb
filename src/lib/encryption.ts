import crypto from 'crypto'

const ALGORITHM = 'aes-256-cbc'
const KEY_LENGTH = 32
const IV_LENGTH = 16

// Get encryption key from environment or generate one
function getEncryptionKey(): Buffer {
  const key = process.env.ENCRYPTION_KEY
  if (!key) {
    throw new Error('ENCRYPTION_KEY environment variable is required')
  }
  
  // If key is hex-encoded, decode it
  if (key.length === KEY_LENGTH * 2) {
    return Buffer.from(key, 'hex')
  }
  
  // Otherwise, hash the key to get consistent 32 bytes
  return crypto.createHash('sha256').update(key).digest()
}

export interface EncryptedData {
  encrypted: string
  iv: string
}

export function encrypt(text: string): EncryptedData {
  const key = getEncryptionKey()
  const iv = crypto.randomBytes(IV_LENGTH)
  
  const cipher = crypto.createCipher(ALGORITHM, key)
  
  let encrypted = cipher.update(text, 'utf8', 'hex')
  encrypted += cipher.final('hex')
  
  return {
    encrypted,
    iv: iv.toString('hex')
  }
}

export function decrypt(encryptedData: EncryptedData): string {
  const key = getEncryptionKey()
  
  const decipher = crypto.createDecipher(ALGORITHM, key)
  
  let decrypted = decipher.update(encryptedData.encrypted, 'hex', 'utf8')
  decrypted += decipher.final('utf8')
  
  return decrypted
}

// Utility functions for database storage
export function encryptForStorage(text: string): string {
  const encrypted = encrypt(text)
  return JSON.stringify(encrypted)
}

export function decryptFromStorage(encryptedString: string): string {
  const encryptedData = JSON.parse(encryptedString) as EncryptedData
  return decrypt(encryptedData)
}

// Validate encryption key format
export function validateEncryptionKey(key: string): boolean {
  try {
    // Test encryption/decryption
    const testData = 'test'
    const originalKey = process.env.ENCRYPTION_KEY
    process.env.ENCRYPTION_KEY = key
    
    const encrypted = encrypt(testData)
    const decrypted = decrypt(encrypted)
    
    // Restore original key
    if (originalKey) {
      process.env.ENCRYPTION_KEY = originalKey
    }
    
    return decrypted === testData
  } catch {
    return false
  }
}