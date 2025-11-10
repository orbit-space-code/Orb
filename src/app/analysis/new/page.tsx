'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ToolSelector from '@/components/analysis/ToolSelector';

interface Codebase {
  id: string;
  name: string;
  description?: string;
}

export default function NewAnalysisPage() {
  const router = useRouter();
  const [codebases, setCodebases] = useState<Codebase[]>([]);
  const [selectedCodebase, setSelectedCodebase] = useState('');
  const [mode, setMode] = useState('standard');
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCodebases();
  }, []);

  const fetchCodebases = async () => {
    try {
      const response = await fetch('/api/codebases');
      const data = await response.json();
      setCodebases(data);
    } catch (error) {
      console.error('Error fetching codebases:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('/api/analysis/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          codebaseId: selectedCodebase,
          mode,
          toolsSelected: selectedTools.length > 0 ? selectedTools : undefined,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start analysis');
      }

      const data = await response.json();
      router.push(`/analysis/${data.id}`);
    } catch (error) {
      console.error('Error starting analysis:', error);
      alert('Failed to start analysis. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">New Analysis</h1>
          <p className="mt-2 text-gray-600">
            Configure and start a new codebase analysis
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Codebase Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Codebase
            </label>
            <select
              value={selectedCodebase}
              onChange={(e) => setSelectedCodebase(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">Choose a codebase...</option>
              {codebases.map((codebase) => (
                <option key={codebase.id} value={codebase.id}>
                  {codebase.name}
                </option>
              ))}
            </select>
            {codebases.length === 0 && (
              <p className="mt-2 text-sm text-gray-500">
                No codebases found.{' '}
                <a href="/codebases/new" className="text-indigo-600 hover:text-indigo-700">
                  Import a codebase
                </a>{' '}
                first.
              </p>
            )}
          </div>

          {/* Analysis Mode */}
          <div className="bg-white rounded-lg shadow p-6">
            <label className="block text-sm font-medium text-gray-700 mb-4">
              Analysis Mode
            </label>
            <div className="space-y-3">
              <label className="flex items-start p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="radio"
                  name="mode"
                  value="normal"
                  checked={mode === 'normal'}
                  onChange={(e) => setMode(e.target.value)}
                  className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500"
                />
                <div className="ml-3">
                  <div className="font-medium text-gray-900">Normal (5 min)</div>
                  <div className="text-sm text-gray-500">
                    Basic static analysis and linting
                  </div>
                </div>
              </label>
              <label className="flex items-start p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="radio"
                  name="mode"
                  value="standard"
                  checked={mode === 'standard'}
                  onChange={(e) => setMode(e.target.value)}
                  className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500"
                />
                <div className="ml-3">
                  <div className="font-medium text-gray-900">Standard (20 min)</div>
                  <div className="text-sm text-gray-500">
                    Comprehensive analysis with security scanning
                  </div>
                </div>
              </label>
              <label className="flex items-start p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="radio"
                  name="mode"
                  value="deep"
                  checked={mode === 'deep'}
                  onChange={(e) => setMode(e.target.value)}
                  className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500"
                />
                <div className="ml-3">
                  <div className="font-medium text-gray-900">Deep (60 min)</div>
                  <div className="text-sm text-gray-500">
                    All tools with advanced security and performance analysis
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Tool Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <ToolSelector
              selectedTools={selectedTools}
              onToolsChange={setSelectedTools}
            />
            <p className="mt-4 text-sm text-gray-500">
              Leave empty to use default tools for the selected mode
            </p>
          </div>

          {/* Submit */}
          <div className="flex justify-end gap-4">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !selectedCodebase}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Starting...' : 'Start Analysis'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
