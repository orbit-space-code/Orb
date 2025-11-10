import Redis from 'ioredis'

// For Upstash Redis, we need to use a different approach
// Upstash provides REST API, but ioredis expects standard Redis protocol

let redis: Redis | null = null

export function getRedisClient(): Redis {
  if (!redis) {
    const redisUrl = process.env.REDIS_URL

    if (redisUrl?.startsWith('https://')) {
      // For Upstash Redis, we'll use a custom implementation
      // Since ioredis doesn't directly support Upstash's HTTP API
      throw new Error('Upstash Redis requires HTTP client, not ioredis. Use server-side Python client instead.')
    } else {
      // Standard Redis connection
      redis = new Redis(redisUrl || 'redis://localhost:6379', {
        enableReadyCheck: false,
        maxRetriesPerRequest: null,
      })
    }
  }

  return redis
}

// For Upstash Redis in Next.js, we'll create a simple HTTP client
export class UpstashRedisClient {
  private url: string
  private token: string

  constructor(url: string, token: string) {
    this.url = url
    this.token = token
  }

  private async request(command: string[]): Promise<any> {
    const response = await fetch(this.url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(command),
    })

    if (!response.ok) {
      throw new Error(`Upstash Redis error: ${response.status}`)
    }

    const data = await response.json()
    return data.result
  }

  async ping(): Promise<string> {
    return await this.request(['PING'])
  }

  async set(key: string, value: string, ex?: number): Promise<string> {
    if (ex) {
      return await this.request(['SET', key, value, 'EX', ex.toString()])
    }
    return await this.request(['SET', key, value])
  }

  async get(key: string): Promise<string | null> {
    return await this.request(['GET', key])
  }

  async del(key: string): Promise<number> {
    return await this.request(['DEL', key])
  }

  async exists(key: string): Promise<number> {
    return await this.request(['EXISTS', key])
  }

  async lpush(key: string, ...values: string[]): Promise<number> {
    return await this.request(['LPUSH', key, ...values])
  }

  async rpush(key: string, ...values: string[]): Promise<number> {
    return await this.request(['RPUSH', key, ...values])
  }

  async lpop(key: string): Promise<string | null> {
    return await this.request(['LPOP', key])
  }

  async rpop(key: string): Promise<string | null> {
    return await this.request(['RPOP', key])
  }

  async llen(key: string): Promise<number> {
    return await this.request(['LLEN', key])
  }
}

// Export the appropriate client based on environment
export function getUpstashRedisClient(): UpstashRedisClient {
  const redisUrl = process.env.REDIS_URL
  const redisToken = process.env.REDIS_TOKEN

  if (!redisUrl || !redisToken) {
    throw new Error('REDIS_URL and REDIS_TOKEN environment variables are required for Upstash Redis')
  }

  return new UpstashRedisClient(redisUrl, redisToken)
}