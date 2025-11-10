"""
End-to-end integration tests for GitHub PR workflow
Tests the complete workflow from implementation to PR creation
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch
from src.github.pr_automation import PRAutomationService
from src.github.pull_request_service import PullRequestService, FileChange
from src.github.pr_labeling import PRLabelingService
from src.github.pr_templates import PRTemplateManager, ChangeType


class TestGitHubWorkflowIntegration:
    """Integration tests for complete GitHub PR workflow"""

    @pytest.fixture
    def real_workspace_setup(self):
        """Create a realistic workspace setup for testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Create project structure
        project_id = "orbitspace-test-123"
        workspace_path = os.path.join(temp_dir, project_id)
        os.makedirs(workspace_path)
        
        # Create frontend repository
        frontend_path = os.path.join(workspace_path, "frontend")
        os.makedirs(frontend_path)
        
        # Initialize git repo
        os.system(f"cd {frontend_path} && git init")
        os.system(f"cd {frontend_path} && git config user.name 'OrbitSpace Bot'")
        os.system(f"cd {frontend_path} && git config user.email 'bot@orbitspace.org'")
        
        # Create initial files
        files_to_create = {
            "package.json": '{"name": "orbitspace-frontend", "version": "1.0.0"}',
            "src/App.tsx": "import React from 'react';\n\nexport default function App() {\n  return <div>Hello OrbitSpace</div>;\n}",
            "src/components/Header.tsx": "import React from 'react';\n\nexport default function Header() {\n  return <header>OrbitSpace</header>;\n}",
            "README.md": "# OrbitSpace Frontend\n\nReact application for OrbitSpace platform."
        }
        
        for file_path, content in files_to_create.items():
            full_path = os.path.join(frontend_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
        
        # Initial commit
        os.system(f"cd {frontend_path} && git add .")
        os.system(f"cd {frontend_path} && git commit -m 'Initial commit'")
        
        # Create feature branch
        feature_branch = f"orbitspace/{project_id}-user-dashboard-20241110"
        os.system(f"cd {frontend_path} && git checkout -b {feature_branch}")
        
        # Add feature implementation
        feature_files = {
            "src/components/Dashboard.tsx": """import React, { useState, useEffect } from 'react';
import { User } from '../types/user';

interface DashboardProps {
  user: User;
}

export default function Dashboard({ user }: DashboardProps) {
  const [analytics, setAnalytics] = useState(null);
  
  useEffect(() => {
    // Fetch analytics data
    fetchAnalytics();
  }, []);
  
  const fetchAnalytics = async () => {
    try {
      const response = await fetch('/api/analytics');
      const data = await response.json();
      setAnalytics(data);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    }
  };
  
  return (
    <div className="dashboard">
      <h1>Welcome, {user.name}!</h1>
      <div className="analytics-section">
        {analytics ? (
          <div>Analytics loaded</div>
        ) : (
          <div>Loading analytics...</div>
        )}
      </div>
    </div>
  );
}""",
            "src/types/user.ts": """export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
  createdAt: string;
}

export interface Analytics {
  totalUsers: number;
  activeProjects: number;
  completedTasks: number;
}""",
            "src/styles/dashboard.css": """.dashboard {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard h1 {
  color: #2563eb;
  margin-bottom: 2rem;
}

.analytics-section {
  background: #f8fafc;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}""",
            "tests/components/Dashboard.test.tsx": """import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import Dashboard from '../../src/components/Dashboard';

const mockUser = {
  id: '1',
  name: 'John Doe',
  email: 'john@orbitspace.org',
  role: 'user' as const,
  createdAt: '2024-01-01T00:00:00Z'
};

// Mock fetch
global.fetch = jest.fn();

describe('Dashboard', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  it('renders user welcome message', () => {
    render(<Dashboard user={mockUser} />);
    expect(screen.getByText('Welcome, John Doe!')).toBeInTheDocument();
  });

  it('fetches analytics on mount', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      json: async () => ({ totalUsers: 100, activeProjects: 25 })
    });

    render(<Dashboard user={mockUser} />);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/analytics');
    });
  });

  it('handles analytics fetch error', async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'));
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

    render(<Dashboard user={mockUser} />);
    
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to fetch analytics:', expect.any(Error));
    });

    consoleSpy.mockRestore();
  });
});"""
        }
        
        for file_path, content in feature_files.items():
            full_path = os.path.join(frontend_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
        
        # Update existing files
        readme_update = """# OrbitSpace Frontend

React application for OrbitSpace platform.

## Features

- User Dashboard with analytics
- Real-time data visualization
- Responsive design
- Comprehensive testing

## Recent Updates

- Added user dashboard component
- Implemented analytics integration
- Added TypeScript type definitions
- Enhanced styling with CSS modules
"""
        
        with open(os.path.join(frontend_path, "README.md"), 'w') as f:
            f.write(readme_update)
        
        # Commit feature implementation
        os.system(f"cd {frontend_path} && git add .")
        os.system(f"cd {frontend_path} && git commit -m 'Implement user dashboard with analytics integration'")
        
        yield {
            'temp_dir': temp_dir,
            'workspace_path': workspace_path,
            'frontend_path': frontend_path,
            'project_id': project_id,
            'feature_branch': feature_branch
        }
        
        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_github_services(self):
        """Create mock GitHub services for integration testing"""
        # Mock PR Service
        pr_service = Mock(spec=PullRequestService)
        pr_service.get_repository_metadata = AsyncMock(return_value={
            'owner': 'orbitspace',
            'repo': 'frontend',
            'full_name': 'orbitspace/frontend',
            'default_branch': 'main',
            'private': False,
            'has_branch_protection': True,
            'protection_rules': {
                'required_pull_request_reviews': {
                    'required_approving_review_count': 1
                }
            }
        })
        
        pr_service.create_pull_request_with_template = AsyncMock(return_value={
            'pr_number': 42,
            'pr_url': 'https://github.com/orbitspace/frontend/pull/42',
            'title': '✨ Feature: Implement user dashboard with analytics integration',
            'draft': True,  # Draft due to branch protection
            'created_at': '2024-11-10T12:00:00Z',
            'labels': ['type: feature', 'scope: frontend', 'orbitspace: ai-generated'],
            'change_type': 'feature'
        })
        
        pr_service.add_agent_recommendations = AsyncMock(return_value=True)
        pr_service.handle_merge_conflicts = AsyncMock(return_value={
            'has_conflicts': False,
            'status': 'clean'
        })
        pr_service._add_pr_labels = AsyncMock(return_value=None)
        pr_service._parse_repository_url = Mock(return_value=('orbitspace', 'frontend'))
        
        # Mock DB Client
        db_client = Mock()
        db_client.project = Mock()
        db_client.project.findUnique = AsyncMock(return_value={
            'id': 'orbitspace-test-123',
            'description': 'Implement user dashboard with real-time analytics',
            'repositories': [
                {
                    'name': 'frontend',
                    'url': 'https://github.com/orbitspace/frontend',
                    'branch': 'orbitspace/orbitspace-test-123-user-dashboard-20241110'
                }
            ]
        })
        
        return {
            'pr_service': pr_service,
            'db_client': db_client
        }

    @pytest.mark.asyncio
    async def test_complete_pr_workflow_integration(self, real_workspace_setup, mock_github_services):
        """Test complete PR workflow from implementation to creation"""
        workspace_data = real_workspace_setup
        services = mock_github_services
        
        # Create PR automation service
        pr_automation = PRAutomationService(services['pr_service'], services['db_client'])
        
        # Test the complete workflow
        result = await pr_automation.create_prs_for_project(
            project_id=workspace_data['project_id'],
            workspace_path=workspace_data['workspace_path'],
            implementation_summary="Implemented comprehensive user dashboard with real-time analytics, TypeScript types, and comprehensive testing",
            agent_recommendations=[
                "Consider adding error boundaries for better error handling",
                "Implement caching for analytics data to improve performance",
                "Add loading states for better user experience",
                "Consider adding unit tests for the analytics service"
            ]
        )
        
        # Verify workflow results
        assert result['project_id'] == workspace_data['project_id']
        assert result['total_repositories'] == 1
        assert result['successful_prs'] == 1
        assert result['failed_prs'] == 0
        
        # Verify PR creation details
        pr_result = result['results'][0]
        assert pr_result['success'] is True
        assert pr_result['pr_data']['pr_number'] == 42
        assert pr_result['pr_data']['draft'] is True  # Due to branch protection
        assert 'orbitspace: ai-generated' in pr_result['pr_data']['labels']
        
        # Verify service interactions
        services['pr_service'].get_repository_metadata.assert_called_once()
        services['pr_service'].create_pull_request_with_template.assert_called_once()
        services['pr_service'].add_agent_recommendations.assert_called_once()

    @pytest.mark.asyncio
    async def test_pr_labeling_integration_with_real_changes(self, real_workspace_setup):
        """Test PR labeling with real file changes from workspace"""
        workspace_data = real_workspace_setup
        
        # Create labeling service
        labeling_service = PRLabelingService()
        
        # Simulate file changes from the real workspace
        file_changes = [
            FileChange("src/components/Dashboard.tsx", "added", 45, 0),
            FileChange("src/types/user.ts", "added", 15, 0),
            FileChange("src/styles/dashboard.css", "added", 20, 0),
            FileChange("tests/components/Dashboard.test.tsx", "added", 35, 0),
            FileChange("README.md", "modified", 8, 4)
        ]
        
        # Analyze and generate labels
        labels = labeling_service.analyze_and_label_pr(
            file_changes=file_changes,
            pr_title="Feature: Implement user dashboard with analytics integration",
            pr_description="Comprehensive user dashboard implementation with real-time analytics, TypeScript types, responsive design, and comprehensive testing suite",
            is_draft=True,
            project_context={
                'project_id': workspace_data['project_id'],
                'phase': 'implementation',
                'type': 'web_application'
            }
        )
        
        # Verify comprehensive labeling
        expected_labels = [
            "type: feature",
            "scope: frontend",
            "size: s",  # Small to medium size
            "status: draft",
            "orbitspace: ai-generated",
            "orbitspace: automated"
        ]
        
        for expected_label in expected_labels:
            assert expected_label in labels, f"Expected label '{expected_label}' not found in {labels}"
        
        # Verify no inappropriate labels
        assert "type: bugfix" not in labels
        assert "type: security" not in labels
        assert "status: ready" not in labels  # Should be draft

    @pytest.mark.asyncio
    async def test_pr_template_integration_with_real_context(self, real_workspace_setup):
        """Test PR template generation with real project context"""
        workspace_data = real_workspace_setup
        
        # Create template manager
        template_manager = PRTemplateManager()
        
        # Simulate file changes
        file_changes = [
            FileChange("src/components/Dashboard.tsx", "added", 45, 0),
            FileChange("src/types/user.ts", "added", 15, 0),
            FileChange("tests/components/Dashboard.test.tsx", "added", 35, 0)
        ]
        
        # Detect change type
        change_type = template_manager.detect_change_type(
            file_changes, 
            "Implement user dashboard with analytics integration"
        )
        
        assert change_type == ChangeType.FEATURE
        
        # Generate PR content
        pr_content = template_manager.generate_pr_content(
            change_type=change_type,
            project_id=workspace_data['project_id'],
            description="Implement user dashboard with analytics integration",
            changes_summary="Added Dashboard component, TypeScript types, and comprehensive tests",
            implementation_details="Implemented responsive user dashboard with real-time analytics integration, proper TypeScript typing, and comprehensive test coverage",
            timestamp="2024-11-10 12:00:00 UTC"
        )
        
        # Verify PR content
        assert pr_content['title'].startswith("✨ Feature:")
        assert "user dashboard" in pr_content['title'].lower()
        assert "Dashboard component" in pr_content['body']
        assert "TypeScript types" in pr_content['body']
        assert workspace_data['project_id'] in pr_content['body']
        assert "orbitspace.org" in pr_content['body']
        
        # Verify labels
        expected_labels = ['feature', 'enhancement', 'automated', 'orb-generated']
        for label in expected_labels:
            assert label in pr_content['labels']

    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self, real_workspace_setup, mock_github_services):
        """Test error handling in the complete workflow"""
        workspace_data = real_workspace_setup
        services = mock_github_services
        
        # Simulate GitHub API error
        services['pr_service'].create_pull_request_with_template.side_effect = Exception("GitHub API rate limit exceeded")
        
        # Create PR automation service
        pr_automation = PRAutomationService(services['pr_service'], services['db_client'])
        
        # Test workflow with error
        result = await pr_automation.create_prs_for_project(
            project_id=workspace_data['project_id'],
            workspace_path=workspace_data['workspace_path'],
            implementation_summary="Test implementation with error"
        )
        
        # Verify error handling
        assert result['project_id'] == workspace_data['project_id']
        assert result['successful_prs'] == 0
        assert result['failed_prs'] == 1
        
        # Verify error details
        pr_result = result['results'][0]
        assert pr_result['success'] is False
        assert "GitHub API rate limit exceeded" in pr_result['error']

    @pytest.mark.asyncio
    async def test_recommended_reviewers_integration(self, real_workspace_setup):
        """Test recommended reviewers based on real file changes"""
        workspace_data = real_workspace_setup
        
        # Create labeling service
        labeling_service = PRLabelingService()
        
        # Test with frontend changes
        frontend_changes = [
            FileChange("src/components/Dashboard.tsx", "added", 45, 0),
            FileChange("src/styles/dashboard.css", "added", 20, 0)
        ]
        
        reviewers = labeling_service.get_recommended_reviewers(
            file_changes=frontend_changes,
            project_context={'project_id': workspace_data['project_id']}
        )
        
        assert 'frontend-team' in reviewers
        assert 'orbitspace-ai-review' in reviewers
        
        # Test with backend changes
        backend_changes = [
            FileChange("src/api/analytics.py", "added", 80, 0),
            FileChange("src/models/user.py", "modified", 20, 10)
        ]
        
        reviewers = labeling_service.get_recommended_reviewers(
            file_changes=backend_changes,
            project_context={'project_id': workspace_data['project_id']}
        )
        
        assert 'backend-team' in reviewers
        assert 'orbitspace-ai-review' in reviewers

    def test_label_definitions_for_orbitspace(self):
        """Test that label definitions are properly configured for OrbitSpace"""
        labeling_service = PRLabelingService()
        definitions = labeling_service.create_label_definitions()
        
        # Verify OrbitSpace-specific labels
        orbitspace_labels = [d for d in definitions if 'orbitspace' in d['name']]
        assert len(orbitspace_labels) >= 2
        
        # Verify required label categories
        categories = {
            'type': [d for d in definitions if d['name'].startswith('type:')],
            'scope': [d for d in definitions if d['name'].startswith('scope:')],
            'priority': [d for d in definitions if d['name'].startswith('priority:')],
            'size': [d for d in definitions if d['name'].startswith('size:')],
            'status': [d for d in definitions if d['name'].startswith('status:')]
        }
        
        # Verify each category has appropriate labels
        assert len(categories['type']) >= 6  # feature, bugfix, refactor, docs, config, tests, performance, security
        assert len(categories['scope']) >= 3  # frontend, backend, database, infrastructure
        assert len(categories['priority']) >= 2  # high, medium, low
        assert len(categories['size']) == 5   # xs, s, m, l, xl
        assert len(categories['status']) >= 2  # draft, ready
        
        # Verify color codes are valid
        for definition in definitions:
            color = definition['color']
            assert len(color) == 6, f"Invalid color code: {color}"
            assert all(c in '0123456789abcdef' for c in color.lower()), f"Invalid hex color: {color}"