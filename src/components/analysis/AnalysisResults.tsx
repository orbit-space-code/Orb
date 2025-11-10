'use client';

import { useState } from 'react';

interface Issue {
  file_path: string;
  line_number?: number;
  severity: string;
  category: string;
  rule_id: string;
  message: string;
  suggestion?: string;
}

interface AnalysisResultsProps {
  results: {
    summary: {
      total_issues: number;
      critical_issues: number;
      high_issues: number;
      medium_issues: number;
      low_issues: number;
      security_issues: number;
      bug_issues: number;
      files_analyzed: number;
      lines_analyzed: number;
    };
    issues: Issue[];
  };
}

export default function AnalysisResults({ results }: AnalysisResultsProps) {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const filteredIssues = results.issues.filter((issue) => {
    if (selectedSeverity !== 'all' && issue.severity !== selectedSeverity) {
      return false;
    }
    if (selectedCategory !== 'all' && issue.category !== selectedCategory) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total Issues</div>
          <div className="text-3xl font-bold text-gray-900 mt-1">
            {results.summary.total_issues}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Critical</div>
          <div className="text-3xl font-bold text-red-600 mt-1">
            {results.summary.critical_issues}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">High</div>
          <div className="text-3xl font-bold text-orange-600 mt-1">
            {results.summary.high_issues}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Medium</div>
          <div className="text-3xl font-bold text-yellow-600 mt-1">
            {results.summary.medium_issues}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Severity
            </label>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="all">All Categories</option>
              <option value="security">Security</option>
              <option value="bug">Bug</option>
              <option value="code_smell">Code Smell</option>
              <option value="style">Style</option>
              <option value="performance">Performance</option>
            </select>
          </div>
        </div>
      </div>

      {/* Issues List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Issues ({filteredIssues.length})
          </h3>
        </div>
        <div className="divide-y divide-gray-200">
          {filteredIssues.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-500">
              No issues found matching the selected filters
            </div>
          ) : (
            filteredIssues.map((issue, index) => (
              <div key={index} className="px-4 py-4 hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`px-2 py-1 text-xs font-semibold rounded border ${getSeverityColor(
                          issue.severity
                        )}`}
                      >
                        {issue.severity.toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-500">
                        {issue.category}
                      </span>
                      <code className="text-sm text-gray-600 bg-gray-100 px-2 py-1 rounded">
                        {issue.rule_id}
                      </code>
                    </div>
                    <p className="text-sm text-gray-900 mb-1">{issue.message}</p>
                    <p className="text-sm text-gray-500">
                      {issue.file_path}
                      {issue.line_number && `:${issue.line_number}`}
                    </p>
                    {issue.suggestion && (
                      <div className="mt-2 text-sm text-indigo-600 bg-indigo-50 px-3 py-2 rounded">
                        💡 {issue.suggestion}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
