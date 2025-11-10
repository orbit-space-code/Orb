"""
Integration tests for GitHub PR system
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from src.github.pull_request_service import PullRequestService, FileChange
from src.github.pr_templates import PRTemplateManager, ChangeType


class TestGitHubIntegration:
    """Integration tests for GitHub PR functionality"""

    @pytest.fixture
    def pr_service(self, mock_redis_client):
        """Create PullRequestService with mocked dependencies"""
        with patch.dict('os.environ', {
            'GITHUB_APP_ID': '123456',
            'GITHUB_APP_PRIVATE_KEY': '''-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdef...
-----END RSA PRIVATE KEY-----'''
        }):
            return PullRequestService(redis_client=mock_redis_client)

    @pytest.fixture
    def mock_github_responses(self):
        """Mock GitHub API responses for integration tests"""
        return {
            'installation': {'id': 12345},
            'access_token': {'token': 'ghs_test_token'},
            'repository': {
                'full_name': 'test-owner/test-repo',
                'default_branch': 'main',
                'private': False,
                'clone_url': 'https://github.com/test-owner/test-repo.git',
                'ssh_url': 'git@github.com:test-owner/test-repo.git',
                'updated_at': '2023-01-01T00:00:00Z'
            },
            'branch_protection': {
                'required_pull_request_reviews': {
                    'required_approving_review_count': 1
                }
            },
            'create_pr': {
                'number': 123,
                'html_url': 'https://github.com/test-owner/test-repo/pull/123',
                'title': '✨ Feature: Test implementation',
                'draft': False,
                'created_at': '2023-01-01T00:00:00Z',
                'head': {'ref': 'feature-branch'},
                'base': {'ref': 'main'}
            },
            'add_labels': {'id': 456}
        }

    @pytest.mark.asyncio
    async def test_full_pr_creation_workflow(self, pr_service, mock_github_responses, mock_db_client):
        """Test complete PR creation workflow"""
        file_changes = [
            FileChange("src/auth.py", "added", 50, 0),
            FileChange("tests/test_auth.py", "added", 30, 0),
            FileChange("README.md", "modified", 5, 2)
        ]
        
        with patch.object(pr_service, '_make_github_request') as mock_request:
            # Mock API call sequence
            mock_request.side_effect = [
                mock_github_responses['repository'],      # Get repo metadata
                mock_github_responses['branch_protection'], # Get branch protection
                mock_github_responses['create_pr'],       # Create PR
                mock_github_responses['add_labels']       # Add labels
            ]
            
            result = await pr_service.create_pull_request_with_template(
                project_id="test-project-123",
                repository_url="https://github.com/test-owner/test-repo",
                feature_branch="feature-auth-system",
                implementation_summary="Implement user authentication system",
                file_changes=file_changes,
                db_client=mock_db_client
            )
            
            # Verify result
            assert result['pr_number'] == 123
            assert result['pr_url'] == 'https://github.com/test-owner/test-repo/pull/123'
            assert result['draft'] is False
            assert 'feature' in result['labels']
            assert 'python' in result['labels']
            assert 'tests' in result['labels']
            
            # Verify API calls
            assert mock_request.call_count == 4
            
            # Verify database tracking
            mock_db_client.pullRequest.create.assert_called_once()
            create_call = mock_db_client.pullRequest.create.call_args
            assert create_call[0][0]['data']['projectId'] == "test-project-123"
            assert create_call[0][0]['data']['prNumber'] == 123

    @pytest.mark.asyncio
    async def test_pr_creation_with_branch_protection(self, pr_service, mock_github_responses, mock_db_client):
        """Test PR creation with branch protection requiring draft"""
        file_changes = [
            FileChange("src/feature.py", "added", 100, 0)
        ]
        
        # Mock branch protection that requires draft
        protected_response = {
            'required_pull_request_reviews': {
                'required_approving_review_count': 2
            },
            'required_status_checks': {
                'contexts': ['ci/test']
            }
        }
        
        with patch.object(pr_service, '_make_github_request') as mock_request:
            mock_request.side_effect = [
                mock_github_responses['repository'],
                protected_response,  # Branch protection requiring draft
                {**mock_github_responses['create_pr'], 'draft': True},  # Draft PR
                mock_github_responses['add_labels']
            ]
            
            result = await pr_service.create_pull_request_with_template(
                project_id="protected-project",
                repository_url="https://github.com/test-owner/test-repo",
                feature_branch="feature-branch",
                implementation_summary="Add new feature",
                file_changes=file_changes,
                db_client=mock_db_client
            )
            
            # Should create draft PR due to protection rules
            assert result['draft'] is True
            
            # Verify PR creation payload included draft: true
            create_pr_call = mock_request.call_args_list[2]
            assert create_pr_call[1]['data']['draft'] is True

    @pytest.mark.asyncio
    async def test_pr_creation_with_merge_conflicts(self, pr_service, mock_github_responses):
        """Test handling PR creation when merge conflicts exist"""
        with patch.object(pr_service, '_make_github_request') as mock_request:
            # Mock PR status with conflicts
            mock_request.return_value = {
                'mergeable_state': 'dirty',
                'number': 123
            }
            
            result = await pr_service.handle_merge_conflicts("owner", "repo", 123)
            
            assert result['has_conflicts'] is True
            assert result['status'] == 'conflicts_detected'
            assert result['comment_added'] is True

    @pytest.mark.asyncio
    async def test_pr_template_selection_based_on_changes(self, pr_service, mock_github_responses, mock_db_client):
        """Test that correct PR template is selected based on file changes"""
        # Test documentation changes
        doc_changes = [
            FileChange("README.md", "modified", 10, 5),
            FileChange("docs/api.md", "added", 50, 0)
        ]
        
        with patch.object(pr_service, '_make_github_request') as mock_request:
            mock_request.side_effect = [
                mock_github_responses['repository'],
                None,  # No branch protection
                {**mock_github_responses['create_pr'], 'title': '📚 Docs: Update documentation'},
                mock_github_responses['add_labels']
            ]
            
            result = await pr_service.create_pull_request_with_template(
                project_id="doc-project",
                repository_url="https://github.com/test-owner/test-repo",
                feature_branch="docs-update",
                implementation_summary="Update API documentation",
                file_changes=doc_changes,
                db_client=mock_db_client
            )
            
            # Should detect documentation change type
            assert 'documentation' in result['labels']
            
            # Verify PR creation used documentation template
            create_pr_call = mock_request.call_args_list[2]
            pr_body = create_pr_call[1]['data']['body']
            assert "Documentation Update" in pr_body

    @pytest.mark.asyncio
    async def test_pr_status_sync_with_github(self, pr_service, mock_db_client):
        """Test syncing PR status between GitHub and database"""
        github_status = {
            'number': 123,
            'state': 'closed',
            'draft': False,
            'merged': True,
            'merged_at': '2023-01-01T12:00:00Z',
            'updated_at': '2023-01-01T12:00:00Z',
            'html_url': 'https://github.com/test-owner/test-repo/pull/123',
            'head': {'sha': 'abc123', 'ref': 'feature-branch'},
            'base': {'ref': 'main'}
        }
        
        with patch.object(pr_service, 'get_pr_status') as mock_status:
            mock_status.return_value = github_status
            
            result = await pr_service.sync_pr_status_with_github(
                mock_db_client,
                "https://github.com/test-owner/test-repo",
                123
            )
            
            assert result['synced'] is True
            assert result['db_status'] == 'MERGED'
            
            # Verify database update
            mock_db_client.pullRequest.update.assert_called_once()
            update_call = mock_db_client.pullRequest.update.call_args
            assert update_call[0][0]['data']['status'] == 'MERGED'
            assert update_call[0][0]['data']['mergedAt'] == '2023-01-01T12:00:00Z'

    @pytest.mark.asyncio
    async def test_get_project_pull_requests(self, pr_service, mock_db_client):
        """Test retrieving all PRs for a project"""
        mock_prs = [
            {
                'id': 'pr-1',
                'prNumber': 123,
                'prUrl': 'https://github.com/test/repo/pull/123',
                'title': 'Feature: Add auth',
                'status': 'OPEN',
                'labels': ['feature', 'python'],
                'isDraft': False,
                'createdAt': '2023-01-01T00:00:00Z',
                'updatedAt': '2023-01-01T00:00:00Z',
                'mergedAt': None,
                'closedAt': None
            },
            {
                'id': 'pr-2',
                'prNumber': 124,
                'prUrl': 'https://github.com/test/repo/pull/124',
                'title': 'Fix: Bug in login',
                'status': 'MERGED',
                'labels': ['bugfix'],
                'isDraft': False,
                'createdAt': '2023-01-02T00:00:00Z',
                'updatedAt': '2023-01-02T12:00:00Z',
                'mergedAt': '2023-01-02T12:00:00Z',
                'closedAt': None
            }
        ]
        
        mock_db_client.pullRequest.findMany.return_value = mock_prs
        
        result = await pr_service.get_project_pull_requests(mock_db_client, "test-project")
        
        assert len(result) == 2
        assert result[0]['pr_number'] == 123
        assert result[0]['status'] == 'OPEN'
        assert result[1]['pr_number'] == 124
        assert result[1]['status'] == 'MERGED'
        
        # Verify database query
        mock_db_client.pullRequest.findMany.assert_called_once_with({
            'where': {'projectId': 'test-project'},
            'orderBy': {'createdAt': 'desc'}
        })

    @pytest.mark.asyncio
    async def test_pr_creation_failure_handling(self, pr_service, mock_db_client):
        """Test handling of PR creation failures"""
        file_changes = [
            FileChange("src/test.py", "added", 10, 0)
        ]
        
        with patch.object(pr_service, '_make_github_request') as mock_request:
            # Mock GitHub API failure
            mock_request.side_effect = Exception("GitHub API error")
            
            with pytest.raises(Exception):
                await pr_service.create_pull_request_with_template(
                    project_id="failing-project",
                    repository_url="https://github.com/test-owner/test-repo",
                    feature_branch="feature-branch",
                    implementation_summary="Test implementation",
                    file_changes=file_changes,
                    db_client=mock_db_client
                )
            
            # Database should not be called on failure
            mock_db_client.pullRequest.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_agent_recommendations_integration(self, pr_service):
        """Test adding agent recommendations to PR"""
        recommendations = [
            "Consider adding input validation",
            "Update error handling patterns",
            "Add logging for debugging"
        ]
        
        with patch.object(pr_service, '_make_github_request') as mock_request:
            mock_request.return_value = {'id': 789}
            
            result = await pr_service.add_agent_recommendations(
                "owner", "repo", 123, recommendations
            )
            
            assert result is True
            
            # Verify comment content
            call_args = mock_request.call_args
            comment_body = call_args[1]['data']['body']
            assert "Agent Recommendations" in comment_body
            assert all(rec in comment_body for rec in recommendations)

    @pytest.mark.asyncio
    async def test_webhook_signature_validation_integration(self, pr_service):
        """Test webhook signature validation with real payload"""
        payload = json.dumps({
            "action": "closed",
            "pull_request": {
                "number": 123,
                "merged": True
            }
        }).encode('utf-8')
        
        secret = "webhook_secret_key"
        
        # Generate valid signature
        import hmac
        import hashlib
        signature = "sha256=" + hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Test valid signature
        assert pr_service.validate_webhook_signature(payload, signature, secret) is True
        
        # Test invalid signature
        invalid_signature = "sha256=invalid_signature_hash"
        assert pr_service.validate_webhook_signature(payload, invalid_signature, secret) is False

    @pytest.mark.asyncio
    async def test_repository_metadata_caching_integration(self, pr_service):
        """Test repository metadata caching behavior"""
        repository_url = "https://github.com/test-owner/test-repo"
        
        mock_repo_data = {
            'full_name': 'test-owner/test-repo',
            'default_branch': 'main',
            'private': False,
            'clone_url': 'https://github.com/test-owner/test-repo.git',
            'ssh_url': 'git@github.com:test-owner/test-repo.git',
            'updated_at': '2023-01-01T00:00:00Z'
        }
        
        with patch.object(pr_service, '_make_github_request') as mock_request:
            with patch.object(pr_service, '_get_branch_protection') as mock_protection:
                mock_request.return_value = mock_repo_data
                mock_protection.return_value = None
                
                # First call - should hit API
                metadata1 = await pr_service.get_repository_metadata(repository_url)
                
                # Second call - should use cache
                metadata2 = await pr_service.get_repository_metadata(repository_url)
                
                # Results should be identical
                assert metadata1 == metadata2
                
                # API should only be called once due to caching
                assert mock_request.call_count == 1
                assert mock_protection.call_count == 1
                
                # Verify cache contains expected data
                assert metadata1['owner'] == 'test-owner'
                assert metadata1['repo'] == 'test-repo'
                assert metadata1['default_branch'] == 'main'