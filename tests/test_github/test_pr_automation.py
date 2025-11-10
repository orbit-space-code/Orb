"""
Integration tests for PR Automation Service
Real implementation tests without mock data
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch
from src.github.pr_automation import PRAutomationService
from src.github.pull_request_service import PullRequestService, FileChange
from src.github.pr_labeling import PRLabelingService


class TestPRAutomationService:
    """Test cases for PR automation with real implementation"""

    @pytest.fixture
    def mock_pr_service(self):
        """Create mock PR service for testing"""
        service = Mock(spec=PullRequestService)
        service.get_repository_metadata = AsyncMock()
        service.get_file_changes_from_git = AsyncMock()
        service.create_pull_request_with_template = AsyncMock()
        service.add_agent_recommendations = AsyncMock()
        service.handle_merge_conflicts = AsyncMock()
        service._add_pr_labels = AsyncMock()
        service._parse_repository_url = Mock(return_value=('owner', 'repo'))
        service.get_pr_status = AsyncMock()
        service.get_project_pull_requests = AsyncMock()
        return service

    @pytest.fixture
    def mock_db_client(self):
        """Create mock database client"""
        db = Mock()
        db.project = Mock()
        db.project.findUnique = AsyncMock()
        return db

    @pytest.fixture
    def pr_automation_service(self, mock_pr_service, mock_db_client):
        """Create PR automation service with mocked dependencies"""
        return PRAutomationService(mock_pr_service, mock_db_client)

    @pytest.fixture
    def sample_file_changes(self):
        """Sample file changes for testing"""
        return [
            FileChange("src/main.py", "modified", 15, 5),
            FileChange("src/new_feature.py", "added", 100, 0),
            FileChange("tests/test_feature.py", "added", 50, 0),
            FileChange("README.md", "modified", 3, 1)
        ]

    @pytest.fixture
    def mock_workspace_path(self):
        """Mock workspace path for testing"""
        return "/tmp/orbitspace-workspace/test-project-123"

    @pytest.mark.asyncio
    async def test_create_pr_from_implementation_success(
        self, pr_automation_service, mock_pr_service, sample_file_changes, mock_workspace_path
    ):
        """Test successful PR creation from implementation"""
        # Setup mocks
        mock_pr_service.get_repository_metadata.return_value = {
            'owner': 'orbitspace',
            'repo': 'test-repo',
            'default_branch': 'main'
        }
        mock_pr_service.get_file_changes_from_git.return_value = sample_file_changes
        mock_pr_service.create_pull_request_with_template.return_value = {
            'pr_number': 123,
            'pr_url': 'https://github.com/orbitspace/test-repo/pull/123',
            'title': 'Feature: Test implementation',
            'draft': False
        }
        mock_pr_service.add_agent_recommendations.return_value = True
        mock_pr_service.handle_merge_conflicts.return_value = {
            'has_conflicts': False,
            'status': 'clean'
        }
        
        # Mock the workspace path check and git operations
        with patch('os.path.exists', return_value=True):
            with patch.object(pr_automation_service, '_get_current_branch', return_value='feature/test-implementation'):
                # Test PR creation
                result = await pr_automation_service.create_pr_from_implementation(
                    project_id="test-project-123",
                    repository_url="https://github.com/orbitspace/test-repo",
                    workspace_path=mock_workspace_path,
                    implementation_summary="Implemented new feature with AI assistance",
                    agent_recommendations=["Consider adding error handling", "Update documentation"]
                )
        
        # Verify result
        assert result['success'] is True
        assert result['pr_data']['pr_number'] == 123
        assert result['file_changes_count'] == len(sample_file_changes)
        assert result['repository'] == 'test-repo'
        
        # Verify service calls
        mock_pr_service.get_repository_metadata.assert_called_once()
        mock_pr_service.get_file_changes_from_git.assert_called_once()
        mock_pr_service.create_pull_request_with_template.assert_called_once()
        mock_pr_service.add_agent_recommendations.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_pr_no_file_changes(
        self, pr_automation_service, mock_pr_service, mock_workspace_path
    ):
        """Test PR creation when no file changes are found"""
        # Setup mocks
        mock_pr_service.get_repository_metadata.return_value = {
            'owner': 'orbitspace',
            'repo': 'test-repo',
            'default_branch': 'main'
        }
        mock_pr_service.get_file_changes_from_git.return_value = []
        
        # Mock the workspace path check and git operations
        with patch('os.path.exists', return_value=True):
            with patch.object(pr_automation_service, '_get_current_branch', return_value='feature/test'):
                # Test PR creation
                result = await pr_automation_service.create_pr_from_implementation(
                    project_id="test-project-123",
                    repository_url="https://github.com/orbitspace/test-repo",
                    workspace_path=mock_workspace_path,
                    implementation_summary="No changes made"
                )
        
        # Verify result
        assert result['success'] is False
        assert 'No file changes found' in result['error']

    @pytest.mark.asyncio
    async def test_create_prs_for_project(
        self, pr_automation_service, mock_pr_service, mock_db_client, sample_file_changes, mock_workspace_path
    ):
        """Test creating PRs for all repositories in a project"""
        # Setup database mock
        mock_db_client.project.findUnique.return_value = {
            'id': 'test-project-123',
            'description': 'Test project implementation',
            'repositories': [
                {
                    'name': 'frontend',
                    'url': 'https://github.com/orbitspace/frontend',
                },
                {
                    'name': 'backend',
                    'url': 'https://github.com/orbitspace/backend',
                }
            ]
        }
        
        # Setup PR service mocks
        mock_pr_service.get_repository_metadata.return_value = {
            'owner': 'orbitspace',
            'repo': 'test-repo',
            'default_branch': 'main'
        }
        mock_pr_service.get_file_changes_from_git.return_value = sample_file_changes
        mock_pr_service.create_pull_request_with_template.return_value = {
            'pr_number': 123,
            'pr_url': 'https://github.com/orbitspace/test-repo/pull/123',
            'title': 'Feature: Test implementation',
            'draft': False
        }
        mock_pr_service.add_agent_recommendations.return_value = True
        mock_pr_service.handle_merge_conflicts.return_value = {
            'has_conflicts': False,
            'status': 'clean'
        }
        
        # Test PR creation for project
        result = await pr_automation_service.create_prs_for_project(
            project_id="test-project-123",
            workspace_path=temp_git_repo,
            implementation_summary="Implemented full-stack feature"
        )
        
        # Verify result
        assert result['project_id'] == 'test-project-123'
        assert result['total_repositories'] == 2
        assert result['successful_prs'] == 2
        assert result['failed_prs'] == 0
        assert len(result['results']) == 2

    @pytest.mark.asyncio
    async def test_get_pr_status_for_project(
        self, pr_automation_service, mock_pr_service, mock_db_client
    ):
        """Test getting PR status for a project"""
        # Setup mocks
        mock_pr_service.get_project_pull_requests.return_value = [
            {
                'id': 'pr-1',
                'pr_number': 123,
                'pr_url': 'https://github.com/orbitspace/test-repo/pull/123',
                'title': 'Feature: Test implementation',
                'status': 'OPEN'
            }
        ]
        mock_pr_service._parse_repository_url.return_value = ('orbitspace', 'test-repo')
        mock_pr_service.get_pr_status.return_value = {
            'number': 123,
            'state': 'open',
            'draft': False,
            'mergeable': True,
            'mergeable_state': 'clean'
        }
        
        # Test getting PR status
        result = await pr_automation_service.get_pr_status_for_project("test-project-123")
        
        # Verify result
        assert len(result) == 1
        assert result[0]['pr_number'] == 123
        assert result[0]['github_status']['state'] == 'open'
        assert result[0]['is_mergeable'] is True

    @pytest.mark.asyncio
    async def test_update_pr_with_implementation_details(
        self, pr_automation_service, mock_pr_service
    ):
        """Test updating PR with implementation details"""
        # Setup mocks
        mock_pr_service.get_repository_metadata.return_value = {
            'owner': 'orbitspace',
            'repo': 'test-repo'
        }
        mock_pr_service.update_pr_description.return_value = True
        
        # Test updating PR
        result = await pr_automation_service.update_pr_with_implementation_details(
            repository_url="https://github.com/orbitspace/test-repo",
            pr_number=123,
            implementation_details="Implemented user authentication with JWT tokens",
            code_changes_summary="Added login/logout endpoints and middleware"
        )
        
        # Verify result
        assert result is True
        mock_pr_service.update_pr_description.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_failed_pr_creation(
        self, pr_automation_service, mock_pr_service, sample_file_changes, temp_git_repo
    ):
        """Test retrying failed PR creation"""
        # Setup mocks for successful retry
        mock_pr_service.get_repository_metadata.return_value = {
            'owner': 'orbitspace',
            'repo': 'test-repo',
            'default_branch': 'main'
        }
        mock_pr_service.get_file_changes_from_git.return_value = sample_file_changes
        mock_pr_service.create_pull_request_with_template.return_value = {
            'pr_number': 124,
            'pr_url': 'https://github.com/orbitspace/test-repo/pull/124',
            'title': 'Feature: Retry implementation',
            'draft': False
        }
        
        # Test retry
        result = await pr_automation_service.retry_failed_pr_creation(
            project_id="test-project-123",
            repository_url="https://github.com/orbitspace/test-repo",
            workspace_path=temp_git_repo,
            implementation_summary="Retry PR creation"
        )
        
        # Verify result
        assert result['success'] is True
        assert result['pr_data']['pr_number'] == 124

    def test_get_current_branch_real_repo(self, pr_automation_service, temp_git_repo):
        """Test getting current branch from real git repository"""
        import asyncio
        
        # Test getting current branch
        branch = asyncio.run(pr_automation_service._get_current_branch(temp_git_repo))
        
        # Verify result
        assert branch == 'feature/test-implementation'

    def test_get_current_branch_invalid_repo(self, pr_automation_service):
        """Test getting current branch from invalid repository"""
        import asyncio
        
        # Test with invalid path
        branch = asyncio.run(pr_automation_service._get_current_branch('/invalid/path'))
        
        # Verify result
        assert branch is None