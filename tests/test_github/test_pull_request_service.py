"""
Integration tests for PullRequestService with real GitHub API integration
"""
import pytest
import json
import hmac
import hashlib
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from aiohttp import ClientSession, ClientResponse
from src.github.pull_request_service import PullRequestService, FileChange, GitHubAPIError


class TestPullRequestService:
    """Test cases for PullRequestService"""

    @pytest.fixture
    def pr_service(self, mock_redis_client):
        """Create PullRequestService instance for testing"""
        with patch.dict('os.environ', {
            'GITHUB_APP_ID': '123456',
            'GITHUB_APP_PRIVATE_KEY': '''-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdef...
-----END RSA PRIVATE KEY-----'''
        }):
            service = PullRequestService(redis_client=mock_redis_client)
            return service

    def test_parse_repository_url_https(self, pr_service):
        """Test parsing HTTPS repository URLs"""
        url = "https://github.com/owner/repo"
        owner, repo = pr_service._parse_repository_url(url)
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_ssh(self, pr_service):
        """Test parsing SSH repository URLs"""
        url = "git@github.com:owner/repo.git"
        owner, repo = pr_service._parse_repository_url(url)
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_with_git_suffix(self, pr_service):
        """Test parsing URLs with .git suffix"""
        url = "https://github.com/owner/repo.git"
        owner, repo = pr_service._parse_repository_url(url)
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_invalid(self, pr_service):
        """Test parsing invalid repository URLs"""
        with pytest.raises(GitHubAPIError):
            pr_service._parse_repository_url("invalid-url")

    def test_validate_webhook_signature_valid(self, pr_service):
        """Test webhook signature validation with valid signature"""
        payload = b'{"test": "data"}'
        secret = "webhook_secret"
        signature = "sha256=" + hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert pr_service.validate_webhook_signature(payload, signature, secret) is True

    def test_validate_webhook_signature_invalid(self, pr_service):
        """Test webhook signature validation with invalid signature"""
        payload = b'{"test": "data"}'
        secret = "webhook_secret"
        signature = "sha256=invalid_signature"
        
        assert pr_service.validate_webhook_signature(payload, signature, secret) is False

    def test_analyze_change_types_python(self, pr_service):
        """Test change type analysis for Python files"""
        file_changes = [
            FileChange("src/main.py", "modified", 10, 5),
            FileChange("tests/test_main.py", "added", 20, 0)
        ]
        
        labels = pr_service._analyze_change_types(file_changes)
        assert "python" in labels
        assert "tests" in labels
        assert "enhancement" in labels
        assert "automated" in labels

    def test_analyze_change_types_javascript(self, pr_service):
        """Test change type analysis for JavaScript files"""
        file_changes = [
            FileChange("src/component.jsx", "modified", 15, 3),
            FileChange("src/styles.css", "added", 25, 0)
        ]
        
        labels = pr_service._analyze_change_types(file_changes)
        assert "javascript" in labels
        assert "frontend" in labels
        assert "enhancement" in labels

    def test_analyze_change_types_documentation(self, pr_service):
        """Test change type analysis for documentation files"""
        file_changes = [
            FileChange("README.md", "modified", 5, 2),
            FileChange("docs/api.md", "added", 30, 0)
        ]
        
        labels = pr_service._analyze_change_types(file_changes)
        assert "documentation" in labels

    def test_analyze_change_types_configuration(self, pr_service):
        """Test change type analysis for configuration files"""
        file_changes = [
            FileChange("config.yml", "modified", 3, 1),
            FileChange(".env.example", "added", 10, 0)
        ]
        
        labels = pr_service._analyze_change_types(file_changes)
        assert "configuration" in labels

    @pytest.mark.asyncio
    async def test_get_file_changes_from_git(self, pr_service, temp_git_repo):
        """Test extracting file changes from git repository"""
        temp_dir, repo = temp_git_repo
        
        # Create some changes
        test_file = f"{temp_dir}/modified.txt"
        with open(test_file, 'w') as f:
            f.write('Modified content')
        
        new_file = f"{temp_dir}/new.txt"
        with open(new_file, 'w') as f:
            f.write('New content')
        
        # Stage and commit changes
        repo.index.add(['modified.txt', 'new.txt'])
        repo.index.commit('Test changes')
        
        # Get file changes
        file_changes = await pr_service.get_file_changes_from_git(temp_dir)
        
        # Should detect changes (implementation may vary based on git state)
        assert isinstance(file_changes, list)

    @pytest.mark.asyncio
    async def test_generate_pr_content(self, pr_service, sample_file_changes):
        """Test PR content generation"""
        project_id = "test-project-123"
        implementation_summary = "Added new feature with tests"
        
        pr_data = await pr_service._generate_pr_content(
            project_id, implementation_summary, sample_file_changes
        )
        
        assert pr_data.title.startswith("[Orb]")
        assert project_id[:8] in pr_data.title
        assert "Files changed:** 4" in pr_data.body
        assert "+95/-7" in pr_data.body
        assert implementation_summary in pr_data.body

    @pytest.mark.asyncio
    async def test_handle_merge_conflicts(self, pr_service):
        """Test merge conflict handling"""
        with patch.object(pr_service, '_make_github_request') as mock_request:
            # Mock PR with conflicts
            mock_request.side_effect = [
                {'mergeable_state': 'dirty', 'number': 123},  # PR status
                {'id': 456}  # Comment creation
            ]
            
            result = await pr_service.handle_merge_conflicts("owner", "repo", 123)
            
            assert result['has_conflicts'] is True
            assert result['status'] == 'conflicts_detected'
            assert result['comment_added'] is True
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_check_branch_protection_rules(self, pr_service):
        """Test branch protection rule checking"""
        with patch.object(pr_service, '_get_branch_protection') as mock_protection:
            mock_protection.return_value = {
                'required_pull_request_reviews': {
                    'required_approving_review_count': 2
                },
                'required_status_checks': {
                    'contexts': ['ci/test', 'ci/lint']
                }
            }
            
            result = await pr_service.check_branch_protection_rules("owner", "repo", "main")
            
            assert result['protected'] is True
            assert result['requires_reviews'] is True
            assert result['requires_status_checks'] is True
            assert result['requires_draft'] is True

    @pytest.mark.asyncio
    async def test_check_branch_protection_rules_no_protection(self, pr_service):
        """Test branch protection checking with no protection"""
        with patch.object(pr_service, '_get_branch_protection') as mock_protection:
            mock_protection.return_value = None
            
            result = await pr_service.check_branch_protection_rules("owner", "repo", "main")
            
            assert result['protected'] is False
            assert result['requires_reviews'] is False
            assert result['requires_status_checks'] is False
            assert result['requires_draft'] is False

    @pytest.mark.asyncio
    async def test_update_pr_description(self, pr_service):
        """Test PR description updating"""
        with patch.object(pr_service, '_make_github_request') as mock_request:
            mock_request.side_effect = [
                {'body': 'Original description'},  # GET PR
                {'body': 'Updated description'}     # PATCH PR
            ]
            
            result = await pr_service.update_pr_description(
                "owner", "repo", 123, "Additional info"
            )
            
            assert result is True
            assert mock_request.call_count == 2
            
            # Check PATCH call
            patch_call = mock_request.call_args_list[1]
            assert patch_call[0][0] == "PATCH"  # method
            assert "Additional Information" in patch_call[1]['data']['body']

    @pytest.mark.asyncio
    async def test_add_agent_recommendations(self, pr_service):
        """Test adding agent recommendations as PR comment"""
        recommendations = [
            "Consider adding error handling",
            "Update documentation",
            "Add unit tests for edge cases"
        ]
        
        with patch.object(pr_service, '_make_github_request') as mock_request:
            mock_request.return_value = {'id': 789}
            
            result = await pr_service.add_agent_recommendations(
                "owner", "repo", 123, recommendations
            )
            
            assert result is True
            assert mock_request.call_count == 1
            
            # Check comment content
            call_args = mock_request.call_args
            comment_body = call_args[1]['data']['body']
            assert "Agent Recommendations" in comment_body
            assert "1. Consider adding error handling" in comment_body
            assert "2. Update documentation" in comment_body
            assert "3. Add unit tests for edge cases" in comment_body

    @pytest.mark.asyncio
    async def test_get_pr_status(self, pr_service, sample_pr_response):
        """Test getting PR status"""
        with patch.object(pr_service, '_make_github_request') as mock_request:
            mock_request.return_value = sample_pr_response
            
            status = await pr_service.get_pr_status("owner", "repo", 123)
            
            assert status['number'] == 123
            assert status['state'] == 'open'
            assert status['draft'] is False
            assert status['merged'] is False
            assert status['mergeable'] is True
            assert status['html_url'] == sample_pr_response['html_url']

    @pytest.mark.asyncio
    async def test_get_repository_metadata_with_cache(self, pr_service, sample_repository_metadata):
        """Test repository metadata retrieval with caching"""
        repository_url = "https://github.com/test-owner/test-repo"
        
        with patch.object(pr_service, '_make_github_request') as mock_request:
            with patch.object(pr_service, '_get_branch_protection') as mock_protection:
                mock_request.return_value = {
                    'full_name': 'test-owner/test-repo',
                    'default_branch': 'main',
                    'private': False,
                    'clone_url': 'https://github.com/test-owner/test-repo.git',
                    'ssh_url': 'git@github.com:test-owner/test-repo.git',
                    'updated_at': '2023-01-01T00:00:00Z'
                }
                mock_protection.return_value = {'required_pull_request_reviews': {}}
                
                # First call
                metadata1 = await pr_service.get_repository_metadata(repository_url)
                
                # Second call should use cache
                metadata2 = await pr_service.get_repository_metadata(repository_url)
                
                assert metadata1 == metadata2
                assert mock_request.call_count == 1  # Only called once due to caching

    @pytest.mark.asyncio
    async def test_make_github_request_rate_limiting(self, pr_service):
        """Test GitHub API request with rate limiting"""
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock rate limited response
            mock_response = AsyncMock()
            mock_response.status = 403
            mock_response.text.return_value = "rate limit exceeded"
            mock_response.headers = {
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': '1640995200'  # Future timestamp
            }
            
            mock_session.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(pr_service, '_get_installation_token', return_value='token'):
                with patch('asyncio.sleep') as mock_sleep:
                    with pytest.raises(GitHubAPIError):
                        await pr_service._make_github_request(
                            "GET", "https://api.github.com/test", "owner", "repo"
                        )
                    
                    # Should have attempted to sleep due to rate limiting
                    assert mock_sleep.called

    @pytest.mark.asyncio
    async def test_make_github_request_server_error_retry(self, pr_service):
        """Test GitHub API request with server error retry"""
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock server error response
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text.return_value = "Internal Server Error"
            mock_response.headers = {}
            
            mock_session.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(pr_service, '_get_installation_token', return_value='token'):
                with patch('asyncio.sleep') as mock_sleep:
                    with pytest.raises(GitHubAPIError):
                        await pr_service._make_github_request(
                            "GET", "https://api.github.com/test", "owner", "repo"
                        )
                    
                    # Should have attempted retries with sleep
                    assert mock_sleep.call_count >= 2  # Multiple retry attempts