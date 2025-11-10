import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { redirect } from 'next/navigation';
import AnalysisDashboard from '@/components/analysis/AnalysisDashboard';

export default async function AnalysisPage() {
  const session = await getServerSession(authOptions);

  if (!session) {
    redirect('/');
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Code Analysis</h1>
          <p className="mt-2 text-gray-600">
            Analyze your codebase with 60+ static analysis, security, and quality tools
          </p>
        </div>

        <AnalysisDashboard />
      </div>
    </div>
  );
}
