"""
Tests for PR Labeling Service
Real implementation tests for comprehensive labeling system
"""
import pytest
from src.github.pr_labeling import PRLabelingService, LabelCategory, LabelRule
from src.github.pull_request_service import FileChange


class TestPRLabelingService:
    """Test cases for PR labeling service"""

    @pytest.fixture
    def labeling_service(self):
        """Create PR labeling service instance"""
        return PRLabelingService()

    @pytest.fixture
    def feature_file_changes(self):
        """File changes for a feature implementation"""
        return [
            FileChange("src/components/UserProfile.tsx", "added", 120, 0),
            FileChange("src/api/users.ts", "added", 80, 0),
            FileChange("src/types/user.ts", "added", 30, 0),
            FileChange("tests/components/UserProfile.test.tsx", "added", 60, 0),
            FileChange("README.md", "modified", 5, 2)
        ]

    @pytest.fixture
    def bugfix_file_changes(self):
        """File changes for a bug fix"""
        return [
            FileChange("src/auth/login.py", "modified", 10, 15),
            FileChange("tests/auth/test_login.py", "modified", 20, 5)
        ]

    @pytest.fixture
    def security_file_changes(self):
        """File changes for security improvements"""
        return [
            FileChange("src/middleware/auth.py", "modified", 50, 20),
            FileChange("src/utils/encryption.py", "added", 100, 0),
            FileChange("requirements.txt", "modified", 2, 1)
        ]

    def test_analyze_feature_implementation(self, labeling_service, feature_file_changes):
        """Test labeling for feature implementation"""
        labels = labeling_service.analyze_and_label_pr(
            file_changes=feature_file_changes,
            pr_title="Feature: Add user profile management",
            pr_description="Implement user profile creation, editing, and viewing functionality",
            is_draft=False
        )
        
        # Verify expected labels
        assert "type: feature" in labels
        assert "scope: frontend" in labels
        assert "scope: backend" in labels
        assert "orbitspace: ai-generated" in labels
        assert "orbitspace: automated" in labels
        assert "size: l" in labels  # Large size based on line changes (297 total)
        
        # Should not have bugfix labels
        assert "type: bugfix" not in labels

    def test_analyze_bugfix_implementation(self, labeling_service, bugfix_file_changes):
        """Test labeling for bug fix"""
        labels = labeling_service.analyze_and_label_pr(
            file_changes=bugfix_file_changes,
            pr_title="Fix: Resolve login authentication issue",
            pr_description="Fix bug where users couldn't log in with special characters in password",
            is_draft=False
        )
        
        # Verify expected labels
        assert "type: bugfix" in labels
        assert "scope: backend" in labels
        assert "orbitspace: ai-generated" in labels
        assert "size: s" in labels  # Small size
        
        # Should not have feature labels
        assert "type: feature" not in labels

    def test_analyze_security_implementation(self, labeling_service, security_file_changes):
        """Test labeling for security improvements"""
        labels = labeling_service.analyze_and_label_pr(
            file_changes=security_file_changes,
            pr_title="Security: Enhance authentication middleware",
            pr_description="Add encryption utilities and improve auth security",
            is_draft=False
        )
        
        # Verify expected labels
        assert "type: security" in labels
        assert "priority: high" in labels
        assert "scope: backend" in labels
        assert "orbitspace: ai-generated" in labels

    def test_analyze_draft_pr(self, labeling_service, feature_file_changes):
        """Test labeling for draft PR"""
        labels = labeling_service.analyze_and_label_pr(
            file_changes=feature_file_changes,
            pr_title="WIP: User profile feature",
            pr_description="Work in progress implementation",
            is_draft=True
        )
        
        # Verify draft status
        assert "status: draft" in labels
        assert "status: ready" not in labels

    def test_analyze_documentation_changes(self, labeling_service):
        """Test labeling for documentation changes"""
        doc_changes = [
            FileChange("README.md", "modified", 20, 5),
            FileChange("docs/api.md", "added", 100, 0),
            FileChange("CONTRIBUTING.md", "modified", 10, 2)
        ]
        
        labels = labeling_service.analyze_and_label_pr(
            file_changes=doc_changes,
            pr_title="Docs: Update API documentation",
            pr_description="Update README and add comprehensive API documentation",
            is_draft=False
        )
        
        # Verify expected labels
        assert "type: documentation" in labels
        assert "priority: low" in labels
        assert "size: s" in labels

    def test_analyze_configuration_changes(self, labeling_service):
        """Test labeling for configuration changes"""
        config_changes = [
            FileChange("docker-compose.yml", "modified", 15, 8),
            FileChange("package.json", "modified", 3, 1),
            FileChange(".env.example", "modified", 5, 2)
        ]
        
        labels = labeling_service.analyze_and_label_pr(
            file_changes=config_changes,
            pr_title="Config: Update Docker configuration",
            pr_description="Update Docker setup and package dependencies",
            is_draft=False
        )
        
        # Verify expected labels
        assert "type: configuration" in labels
        assert "scope: infrastructure" in labels

    def test_analyze_test_changes(self, labeling_service):
        """Test labeling for test-only changes"""
        test_changes = [
            FileChange("tests/unit/test_auth.py", "added", 80, 0),
            FileChange("tests/integration/test_api.py", "modified", 30, 10),
            FileChange("jest.config.js", "modified", 5, 2)
        ]
        
        labels = labeling_service.analyze_and_label_pr(
            file_changes=test_changes,
            pr_title="Tests: Add comprehensive auth testing",
            pr_description="Add unit and integration tests for authentication",
            is_draft=False
        )
        
        # Verify expected labels
        assert "type: tests" in labels
        assert "scope: backend" in labels

    def test_analyze_performance_changes(self, labeling_service):
        """Test labeling for performance improvements"""
        perf_changes = [
            FileChange("src/utils/cache.py", "added", 150, 0),
            FileChange("src/api/endpoints.py", "modified", 40, 60),
            FileChange("requirements.txt", "modified", 2, 0)
        ]
        
        labels = labeling_service.analyze_and_label_pr(
            file_changes=perf_changes,
            pr_title="Performance: Add caching layer",
            pr_description="Optimize API performance with Redis caching",
            is_draft=False
        )
        
        # Verify expected labels
        assert "type: performance" in labels
        assert "scope: backend" in labels

    def test_size_labeling_xs(self, labeling_service):
        """Test XS size labeling"""
        xs_changes = [
            FileChange("src/config.py", "modified", 3, 2)
        ]
        
        labels = labeling_service.analyze_and_label_pr(
            file_changes=xs_changes,
            pr_title="Fix: Update config value",
            pr_description="Small configuration fix",
            is_draft=False
        )
        
        assert "size: xs" in labels

    def test_size_labeling_xl(self, labeling_service):
        """Test XL size labeling"""
        xl_changes = [
            FileChange("src/new_module.py", "added", 300, 0),
            FileChange("src/another_module.py", "added", 250, 0),
            FileChange("tests/test_modules.py", "added", 200, 0)
        ]
        
        labels = labeling_service.analyze_and_label_pr(
            file_changes=xl_changes,
            pr_title="Feature: Major new functionality",
            pr_description="Large feature implementation",
            is_draft=False
        )
        
        assert "size: xl" in labels

    def test_project_context_analysis(self, labeling_service, feature_file_changes):
        """Test labeling with project context"""
        labels = labeling_service.analyze_and_label_pr(
            file_changes=feature_file_changes,
            pr_title="Feature: User management",
            pr_description="Implement user management features",
            is_draft=False,
            project_context={
                'phase': 'implementation',
                'type': 'web_application',
                'priority': 'high'
            }
        )
        
        # Should include context-based labels
        assert "orbitspace: ai-generated" in labels
        assert "type: feature" in labels

    def test_get_recommended_reviewers(self, labeling_service, feature_file_changes):
        """Test getting recommended reviewers"""
        reviewers = labeling_service.get_recommended_reviewers(
            file_changes=feature_file_changes,
            project_context={'project_id': 'test-123'}
        )
        
        # Should recommend appropriate teams
        assert 'frontend-team' in reviewers
        assert 'backend-team' in reviewers
        assert 'orbitspace-ai-review' in reviewers

    def test_get_recommended_reviewers_security(self, labeling_service, security_file_changes):
        """Test getting recommended reviewers for security changes"""
        reviewers = labeling_service.get_recommended_reviewers(
            file_changes=security_file_changes
        )
        
        # Should recommend security team
        assert 'security-team' in reviewers
        assert 'backend-team' in reviewers
        assert 'orbitspace-ai-review' in reviewers

    def test_create_label_definitions(self, labeling_service):
        """Test creating label definitions for repository setup"""
        definitions = labeling_service.create_label_definitions()
        
        # Should have comprehensive label definitions
        assert len(definitions) > 20
        
        # Check for required categories
        type_labels = [d for d in definitions if d['name'].startswith('type:')]
        scope_labels = [d for d in definitions if d['name'].startswith('scope:')]
        size_labels = [d for d in definitions if d['name'].startswith('size:')]
        orbitspace_labels = [d for d in definitions if d['name'].startswith('orbitspace:')]
        
        assert len(type_labels) >= 6  # feature, bugfix, refactor, docs, config, tests, performance, security
        assert len(scope_labels) >= 3  # frontend, backend, database, infrastructure
        assert len(size_labels) == 5   # xs, s, m, l, xl
        assert len(orbitspace_labels) >= 2  # ai-generated, automated
        
        # Verify label structure
        for definition in definitions:
            assert 'name' in definition
            assert 'color' in definition
            assert 'description' in definition
            assert len(definition['color']) == 6  # Valid hex color

    def test_label_rule_priority_system(self, labeling_service):
        """Test that label rules are applied based on priority"""
        # Security should override other type labels due to higher priority
        security_changes = [
            FileChange("src/auth.py", "modified", 20, 10)
        ]
        
        labels = labeling_service.analyze_and_label_pr(
            file_changes=security_changes,
            pr_title="Security fix: Patch authentication vulnerability",
            pr_description="Fix critical security issue in auth system",
            is_draft=False
        )
        
        # Security should be present due to high priority
        assert "type: security" in labels
        assert "priority: high" in labels
        
        # Should still have automation labels
        assert "orbitspace: ai-generated" in labels

    def test_comprehensive_labeling_integration(self, labeling_service):
        """Test comprehensive labeling with complex changes"""
        complex_changes = [
            # Frontend changes
            FileChange("src/components/Dashboard.tsx", "modified", 80, 30),
            FileChange("src/styles/dashboard.css", "added", 50, 0),
            
            # Backend changes
            FileChange("src/api/dashboard.py", "modified", 60, 20),
            FileChange("src/models/analytics.py", "added", 120, 0),
            
            # Database changes
            FileChange("migrations/001_add_analytics.sql", "added", 40, 0),
            
            # Tests
            FileChange("tests/test_dashboard.py", "added", 90, 0),
            
            # Documentation
            FileChange("README.md", "modified", 10, 5)
        ]
        
        labels = labeling_service.analyze_and_label_pr(
            file_changes=complex_changes,
            pr_title="Feature: Add analytics dashboard",
            pr_description="Implement comprehensive analytics dashboard with real-time data visualization",
            is_draft=False,
            project_context={'phase': 'implementation', 'priority': 'high'}
        )
        
        # Should have comprehensive labeling
        assert "type: feature" in labels
        assert "scope: frontend" in labels
        assert "scope: backend" in labels
        assert "scope: database" in labels
        assert "size: l" in labels  # Large due to many changes
        assert "orbitspace: ai-generated" in labels
        assert "orbitspace: automated" in labels
        
        # Should be ready (not draft)
        assert "status: ready" in labels
        assert "status: draft" not in labels