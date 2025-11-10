'use client'

import { useState, useEffect } from 'react'
import Editor from '@monaco-editor/react'

interface MarkdownEditorProps {
  content: string
  onSave: (content: string) => Promise<void>
  readOnly?: boolean
}

export default function MarkdownEditor({
  content,
  onSave,
  readOnly = false,
}: MarkdownEditorProps) {
  const [editorContent, setEditorContent] = useState(content)
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState(false)

  useEffect(() => {
    setEditorContent(content)
  }, [content])

  useEffect(() => {
    setHasChanges(editorContent !== content)
  }, [editorContent, content])

  const handleSave = async () => {
    if (!hasChanges || isSaving) return

    setIsSaving(true)
    setError(null)

    try {
      await onSave(editorContent)
      setHasChanges(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setIsSaving(false)
    }
  }

  const handleRevert = () => {
    setEditorContent(content)
    setHasChanges(false)
  }

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between bg-gray-800 border-b border-gray-700 px-4 py-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPreview(!showPreview)}
            className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
          >
            {showPreview ? 'Edit' : 'Preview'}
          </button>
          {hasChanges && (
            <span className="text-xs text-yellow-400">Unsaved changes</span>
          )}
        </div>

        {!readOnly && (
          <div className="flex items-center gap-2">
            {hasChanges && (
              <button
                onClick={handleRevert}
                disabled={isSaving}
                className="px-3 py-1 text-sm text-gray-400 hover:text-gray-300 disabled:opacity-50"
              >
                Revert
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
              className="px-4 py-1 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-900/30 border-b border-red-700 px-4 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Editor or Preview */}
      <div className="flex-1 overflow-hidden">
        {showPreview ? (
          <div className="h-full overflow-y-auto p-6 prose prose-invert max-w-none">
            <div
              className="markdown-body"
              dangerouslySetInnerHTML={{
                __html: editorContent
                  .split('\n')
                  .map((line) => {
                    // Basic markdown rendering (you can add a proper markdown library)
                    if (line.startsWith('# '))
                      return `<h1>${line.slice(2)}</h1>`
                    if (line.startsWith('## '))
                      return `<h2>${line.slice(3)}</h2>`
                    if (line.startsWith('### '))
                      return `<h3>${line.slice(4)}</h3>`
                    if (line.startsWith('- ')) return `<li>${line.slice(2)}</li>`
                    if (line.startsWith('**') && line.endsWith('**'))
                      return `<strong>${line.slice(2, -2)}</strong>`
                    if (line.trim() === '') return '<br/>'
                    return `<p>${line}</p>`
                  })
                  .join(''),
              }}
            />
          </div>
        ) : (
          <Editor
            height="100%"
            defaultLanguage="markdown"
            value={editorContent}
            onChange={(value) => setEditorContent(value || '')}
            theme="vs-dark"
            options={{
              readOnly,
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              wordWrap: 'on',
              padding: { top: 16, bottom: 16 },
            }}
          />
        )}
      </div>
    </div>
  )
}
