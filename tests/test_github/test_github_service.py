"""
Tests for GitHub service
"""
import os
import pytest
import httpx
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.services.github_service import (
    GitHubService,
    GitUser,
    RepositoryNotFoundError,
    UnauthorizedError,
    RateLimitError
)

# Test data
TEST_REPO_OWNER = "test-owner"
TEST_REPO_NAME = "test-repo"
TEST_BRANCH = "test-branch"
TEST_FILE_PATH = "test/file.py"
TEST_FILE_CONTENT = "print('Hello, World!')"

# Fixtures
@pytest.fixture
def mock_github():
    """Mock GitHub client"""
    with patch('github.Github') as mock_github_class:
        mock_github = mock_github_class.return_value
        
        # Mock user
        mock_user = MagicMock()
        mock_user.login = "test-user"
        mock_github.get_user.return_value = mock_user
        
        # Mock repo
        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo
        
        # Mock branch
        mock_branch = MagicMock()
        mock_branch.name = TEST_BRANCH
        mock_branch.commit.sha = "test-sha"
        mock_repo.get_branch.return_value = mock_branch
        
        # Mock file content
        mock_file = MagicMock()
        mock_file.decoded_content = TEST_FILE_CONTENT.encode()
        mock_file.sha = "file-sha"
        mock_file.size = len(TEST_FILE_CONTENT)
        mock_repo.get_contents.return_value = mock_file
        
        yield mock_github, mock_repo, mock_user

# Tests
def test_github_service_init_success():
    """Test successful GitHub service initialization"""
    with patch.dict(os.environ, {"GITHUB_ACCESS_TOKEN": "test-token"}):
        service = GitHubService()
        assert service is not None

def test_github_service_init_no_auth():
    """Test initialization with no authentication"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(UnauthorizedError):
            GitHubService()

@patch('github.Github')
def test_get_authenticated_user(mock_github_class):
    """Test getting authenticated user"""
    # Setup
    mock_github = mock_github_class.return_value
    mock_user = MagicMock()
    mock_user.login = "test-user"
    mock_user.name = "Test User"
    mock_user.email = "test@example.com"
    mock_user.avatar_url = "https://avatar.url"
    mock_github.get_user.return_value = mock_user
    
    # Test
    service = GitHubService(access_token="test-token")
    user = service.get_authenticated_user()
    
    # Assert
    assert isinstance(user, GitUser)
    assert user.login == "test-user"
    assert user.name == "Test User"
    assert user.email == "test@example.com"

def test_get_repository_not_found(mock_github):
    """Test getting a non-existent repository"""
    mock_github, mock_repo, _ = mock_github
    mock_github.get_repo.side_effect = Exception("Not Found")
    
    service = GitHubService(access_token="test-token")
    
    with pytest.raises(RepositoryNotFoundError):
        service.get_repository("nonexistent", "repo")

def test_rate_limit_handling(mock_github):
    """Test rate limit error handling"""
    mock_github, mock_repo, _ = mock_github
    
    # Create a mocked response with rate limit headers
    response = MagicMock()
    response.headers = {
        'X-RateLimit-Limit': '5000',
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': str(int((datetime.now() + timedelta(minutes=1)).timestamp()))
    }
    
    # Make get_repo raise a RateLimitExceededException
    from github import RateLimitExceededException
    mock_github.get_repo.side_effect = RateLimitExceededException(
        res=response,
        data=b'{"message":"API rate limit exceeded"}'
    )
    
    service = GitHubService(access_token="test-token")
    
    with pytest.raises(RateLimitError) as exc_info:
        service.get_repository(TEST_REPO_OWNER, TEST_REPO_NAME)
    
    assert exc_info.value.time_until_reset() > 0

# Add more test cases for other methods...
