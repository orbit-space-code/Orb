import { z } from 'zod'

// Enums
export enum AnalysisMode {
  NORMAL = 'NORMAL',
  STANDARD = 'STANDARD',
  DEEP = 'DEEP'
}

export enum AnalysisStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED'
}

export enum ToolStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  SKIPPED = 'SKIPPED'
}

export enum SourceType {
  GIT = 'git',
  UPLOAD = 'upload',
  URL = 'url'
}

export enum ReportType {
  SUMMARY = 'summary',
  TECHNICAL = 'technical',
  JSON = 'json',
  COMPLIANCE = 'compliance'
}

export enum ReportFormat {
  PDF = 'pdf',
  HTML = 'html',
  JSON = 'json',
  MARKDOWN = 'md'
}

// API Key Management
export const ApiKeyProviderSchema = z.enum(['anthropic', 'openai', 'custom'])
export type ApiKeyProvider = z.infer<typeof ApiKeyProviderSchema>

export const CreateApiKeySchema = z.object({
  provider: ApiKeyProviderSchema,
  key: z.string().min(1, 'API key is required'),
})

export const UpdateApiKeySchema = z.object({
  key: z.string().min(1, 'API key is required'),
})

export interface UserApiKey {
  id: string
  userId: string
  provider: ApiKeyProvider
  encryptedKey: string
  isActive: boolean
  createdAt: Date
  updatedAt: Date
}

// Codebase Management
export const CreateCodebaseSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  description: z.string().optional(),
  sourceType: z.enum(['git', 'upload', 'url']),
  sourceUrl: z.string().url().optional(),
})

export const UpdateCodebaseSchema = z.object({
  name: z.string().min(1).max(255).optional(),
  description: z.string().optional(),
})

export interface Codebase {
  id: string
  userId: string
  name: string
  description?: string
  sourceType: SourceType
  sourceUrl?: string
  languagePrimary?: string
  languages: string[]
  frameworkInfo: Record<string, any>
  fileCount: number
  lineCount: number
  sizeBytes: bigint
  indexedAt?: Date
  createdAt: Date
  updatedAt: Date
}

export interface CodebaseWithAnalyses extends Codebase {
  analysisSessions: AnalysisSession[]
}

// Analysis Session Management
export const CreateAnalysisSessionSchema = z.object({
  codebaseId: z.string().uuid(),
  mode: z.nativeEnum(AnalysisMode),
  toolsSelected: z.array(z.string()).optional(),
})

export interface AnalysisSession {
  id: string
  codebaseId: string
  userId: string
  mode: AnalysisMode
  status: AnalysisStatus
  toolsSelected: string[]
  startedAt: Date
  completedAt?: Date
  estimatedDuration?: number
  actualDuration?: number
  costEstimate?: number
  actualCost?: number
  errorMessage?: string
}

export interface AnalysisSessionWithResults extends AnalysisSession {
  codebase: Codebase
  toolResults: ToolResult[]
  reports: AnalysisReport[]
}

// Tool Results
export interface ToolResult {
  id: string
  sessionId: string
  toolName: string
  toolVersion?: string
  status: ToolStatus
  startedAt: Date
  completedAt?: Date
  results: Record<string, any>
  metrics?: Record<string, any>
  issues?: Issue[]
  executionTime?: number
  errorMessage?: string
}

export interface Issue {
  id: string
  severity: 'error' | 'warning' | 'info'
  category: string
  message: string
  file?: string
  line?: number
  column?: number
  rule?: string
  suggestion?: string
}

// Analysis Reports
export const GenerateReportSchema = z.object({
  sessionId: z.string().uuid(),
  reportType: z.enum(['summary', 'technical', 'json', 'compliance']),
  format: z.enum(['pdf', 'html', 'json', 'md']),
  includeDetails: z.boolean().default(true),
})

export interface AnalysisReport {
  id: string
  sessionId: string
  reportType: ReportType
  format: ReportFormat
  title: string
  content?: string
  filePath?: string
  fileSize?: number
  generatedAt: Date
}

// Tool Configuration
export interface ToolConfig {
  name: string
  version: string
  category: ToolCategory
  description: string
  supportedLanguages: string[]
  configurable: boolean
  defaultConfig: Record<string, any>
  estimatedDuration: number // seconds
  costWeight: number // relative cost factor
}

export enum ToolCategory {
  STATIC_ANALYSIS = 'static_analysis',
  SECURITY = 'security',
  QUALITY = 'quality',
  PERFORMANCE = 'performance',
  DOCUMENTATION = 'documentation',
  ARCHITECTURE = 'architecture'
}

// Analysis Results Aggregation
export interface AnalysisResults {
  sessionId: string
  summary: AnalysisSummary
  toolResults: ToolResult[]
  issues: Issue[]
  metrics: AnalysisMetrics
  recommendations: Recommendation[]
}

export interface AnalysisSummary {
  totalIssues: number
  criticalIssues: number
  warningIssues: number
  infoIssues: number
  overallScore: number // 0-100
  qualityGrade: 'A' | 'B' | 'C' | 'D' | 'F'
  securityScore: number
  maintainabilityScore: number
  performanceScore: number
}

export interface AnalysisMetrics {
  linesOfCode: number
  cyclomaticComplexity: number
  technicalDebt: number // hours
  testCoverage: number // percentage
  duplicatedLines: number
  codeSmells: number
  vulnerabilities: number
  bugs: number
}

export interface Recommendation {
  id: string
  priority: 'high' | 'medium' | 'low'
  category: string
  title: string
  description: string
  impact: string
  effort: 'low' | 'medium' | 'high'
  files?: string[]
  aiGenerated: boolean
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
    details?: any
  }
  meta?: {
    total?: number
    page?: number
    limit?: number
  }
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  hasNext: boolean
  hasPrev: boolean
}

// WebSocket Events
export interface AnalysisProgressEvent {
  type: 'analysis_progress'
  sessionId: string
  status: AnalysisStatus
  progress: number // 0-100
  currentTool?: string
  message?: string
}

export interface ToolProgressEvent {
  type: 'tool_progress'
  sessionId: string
  toolName: string
  status: ToolStatus
  progress: number
  message?: string
}