"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List

# Test fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.set.return_value = None
    mock_redis.get.return_value = None
    mock_redis.publish.return_value = None
    return mock_redis


@pytest.fixture
def mock_db_client():
    """Mock database client for testing"""
    mock_db = Mock()
    mock_db.pullRequest = Mock()
    mock_db.pullRequest.create = AsyncMock()
    mock_db.pullRequest.update = AsyncMock()
    mock_db.pullRequest.findMany = AsyncMock(return_value=[])
    mock_db.project = Mock()
    mock_db.project.findUnique = AsyncMock()
    return mock_db


@pytest.fixture
def sample_file_changes():
    """Sample file changes for testing"""
    from src.github.pull_request_service import FileChange
    
    return [
        FileChange(path="src/main.py", status="modified", additions=10, deletions=5),
        FileChange(path="src/new_feature.py", status="added", additions=50, deletions=0),
        FileChange(path="tests/test_feature.py", status="added", additions=30, deletions=0),
        FileChange(path="README.md", status="modified", additions=5, deletions=2)
    ]


@pytest.fixture
def sample_repository_metadata():
    """Sample repository metadata for testing"""
    return {
        'owner': 'test-owner',
        'repo': 'test-repo',
        'full_name': 'test-owner/test-repo',
        'default_branch': 'main',
        'private': False,
        'has_branch_protection': True,
        'protection_rules': {
            'required_pull_request_reviews': {
                'required_approving_review_count': 1
            }
        },
        'clone_url': 'https://github.com/test-owner/test-repo.git',
        'ssh_url': 'git@github.com:test-owner/test-repo.git',
        'updated_at': '2023-01-01T00:00:00Z'
    }


@pytest.fixture
def sample_pr_response():
    """Sample GitHub PR API response"""
    return {
        'number': 123,
        'html_url': 'https://github.com/test-owner/test-repo/pull/123',
        'title': '✨ Feature: Test implementation',
        'draft': False,
        'created_at': '2023-01-01T00:00:00Z',
        'updated_at': '2023-01-01T00:00:00Z',
        'state': 'open',
        'merged': False,
        'mergeable': True,
        'mergeable_state': 'clean',
        'head': {
            'ref': 'feature-branch',
            'sha': 'abc123'
        },
        'base': {
            'ref': 'main'
        }
    }


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing"""
    import git
    
    temp_dir = tempfile.mkdtemp()
    repo = git.Repo.init(temp_dir)
    
    # Configure git user
    with repo.config_writer() as git_config:
        git_config.set_value('user', 'name', 'Test User')
        git_config.set_value('user', 'email', 'test@example.com')
    
    # Create initial commit
    test_file = os.path.join(temp_dir, 'test.txt')
    with open(test_file, 'w') as f:
        f.write('Initial content')
    
    repo.index.add(['test.txt'])
    repo.index.commit('Initial commit')
    
    yield temp_dir, repo
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def real_github_config():
    """Real GitHub configuration for OrbitSpace"""
    return {
        'organization': 'orbitspace',
        'app_id': os.getenv('GITHUB_APP_ID', '2238196'),
        'bot_name': 'OrbitSpace-bot',
        'bot_email': 'support@orbitspace.org',
        'base_url': 'https://api.github.com',
        'webhook_secret': os.getenv('GITHUB_WEBHOOK_SECRET', 'test-secret'),
        'repositories': {
            'frontend': 'https://github.com/orbitspace/frontend',
            'backend': 'https://github.com/orbitspace/backend',
            'docs': 'https://github.com/orbitspace/docs'
        }
    }


@pytest.fixture
def orbitspace_webhook_payload():
    """Real OrbitSpace GitHub webhook payload"""
    return {
        'action': 'closed',
        'pull_request': {
            'number': 42,
            'state': 'closed',
            'merged': True,
            'merged_at': '2024-11-10T12:00:00Z',
            'html_url': 'https://github.com/orbitspace/frontend/pull/42',
            'title': '✨ Feature: Implement user dashboard',
            'body': 'Automated PR created by OrbitSpace AI',
            'labels': [
                {'name': 'orbitspace: ai-generated'},
                {'name': 'type: feature'},
                {'name': 'scope: frontend'}
            ]
        },
        'repository': {
            'full_name': 'orbitspace/frontend',
            'clone_url': 'https://github.com/orbitspace/frontend.git',
            'default_branch': 'main'
        },
        'sender': {
            'login': 'orbitspace-bot',
            'type': 'Bot'
        }
    }


@pytest.fixture
def orbitspace_environment():
    """Set up OrbitSpace environment variables"""
    test_env = {
        'GITHUB_APP_ID': '2238196',
        'GITHUB_APP_PRIVATE_KEY': os.getenv('GITHUB_APP_PRIVATE_KEY', 'test-key'),
        'GIT_BOT_NAME': 'OrbitSpace-bot',
        'GIT_BOT_EMAIL': 'support@orbitspace.org',
        'REDIS_URL': 'redis://localhost:6379/1',
        'DATABASE_URL': os.getenv('DATABASE_URL', 'postgresql://test:test@localhost:5432/orbitspace_test')
    }
    
    # Set environment variables
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield test_env
    
    # Clean up environment variables
    for key in test_env.keys():
        if key in os.environ:
            del os.environ[key]