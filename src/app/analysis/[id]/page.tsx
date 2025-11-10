'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import AnalysisResults from '@/components/analysis/AnalysisResults';

interface AnalysisSession {
  id: string;
  mode: string;
  status: string;
  startedAt: string;
  completedAt?: string;
  codebase: {
    name: string;
  };
}

export default function AnalysisDetailPage() {
  const params = useParams();
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [results, setResults] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSession();
    connectToStream();
  }, [params.id]);

  const fetchSession = async () => {
    try {
      const response = await fetch(`/api/analysis/sessions/${params.id}`);
      const data = await response.json();
      setSession(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching session:', error);
      setLoading(false);
    }
  };

  const connectToStream = () => {
    const eventSource = new EventSource(
      `/api/analysis/sessions/${params.id}/stream`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'status_update') {
        setSession((prev) => (prev ? { ...prev, status: data.status } : null));
        if (data.results) {
          setResults(data.results);
        }
      } else {
        setLogs((prev) => [...prev, data]);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'bg-green-100 text-green-800';
      case 'RUNNING':
        return 'bg-blue-100 text-blue-800';
      case 'FAILED':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-yellow-100 text-yellow-800';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900">Session not found</h2>
          <a
            href="/analysis"
            className="mt-4 inline-block text-indigo-600 hover:text-indigo-700"
          >
            Back to Analysis
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {session.codebase.name}
              </h1>
              <p className="mt-2 text-gray-600">
                Mode: {session.mode} • Started:{' '}
                {new Date(session.startedAt).toLocaleString()}
              </p>
            </div>
            <span
              className={`px-4 py-2 rounded-full text-sm font-medium ${getStatusColor(
                session.status
              )}`}
            >
              {session.status}
            </span>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button className="border-b-2 border-indigo-500 py-4 px-1 text-sm font-medium text-indigo-600">
                Results
              </button>
              <button className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
                Logs
              </button>
              <button className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
                Reports
              </button>
            </nav>
          </div>
        </div>

        {/* Content */}
        {session.status === 'RUNNING' && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mr-4"></div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Analysis in progress...
                </h3>
                <p className="text-sm text-gray-500">
                  This may take a few minutes depending on the codebase size
                </p>
              </div>
            </div>
          </div>
        )}

        {results && <AnalysisResults results={results} />}

        {!results && session.status === 'PENDING' && (
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <p className="text-gray-500">Waiting for analysis to start...</p>
          </div>
        )}

        {/* Logs */}
        {logs.length > 0 && (
          <div className="mt-6 bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Activity Log
            </h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {logs.map((log, index) => (
                <div
                  key={index}
                  className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded"
                >
                  {JSON.stringify(log)}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
