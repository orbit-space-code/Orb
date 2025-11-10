"""
Unit tests for PR Templates
"""
import pytest
from src.github.pr_templates import PRTemplateManager, ChangeType, PRTemplate
from src.github.pull_request_service import FileChange


class TestPRTemplateManager:
    """Test cases for PRTemplateManager"""

    @pytest.fixture
    def template_manager(self):
        """Create PRTemplateManager instance for testing"""
        return PRTemplateManager()

    def test_initialization(self, template_manager):
        """Test template manager initialization"""
        assert len(template_manager.templates) == 8
        assert ChangeType.FEATURE in template_manager.templates
        assert ChangeType.BUGFIX in template_manager.templates
        assert ChangeType.REFACTOR in template_manager.templates

    def test_get_template_feature(self, template_manager):
        """Test getting feature template"""
        template = template_manager.get_template(ChangeType.FEATURE)
        
        assert isinstance(template, PRTemplate)
        assert template.title_prefix == "✨ Feature:"
        assert "feature" in template.labels
        assert "enhancement" in template.labels
        assert len(template.checklist) > 0

    def test_get_template_bugfix(self, template_manager):
        """Test getting bugfix template"""
        template = template_manager.get_template(ChangeType.BUGFIX)
        
        assert template.title_prefix == "🐛 Fix:"
        assert "bugfix" in template.labels
        assert "bug" in template.labels
        assert "Root Cause" in template.description_template

    def test_get_template_refactor(self, template_manager):
        """Test getting refactor template"""
        template = template_manager.get_template(ChangeType.REFACTOR)
        
        assert template.title_prefix == "♻️ Refactor:"
        assert "refactor" in template.labels
        assert "cleanup" in template.labels
        assert "No functional changes" in template.description_template

    def test_get_template_documentation(self, template_manager):
        """Test getting documentation template"""
        template = template_manager.get_template(ChangeType.DOCUMENTATION)
        
        assert template.title_prefix == "📚 Docs:"
        assert "documentation" in template.labels
        assert "docs" in template.labels

    def test_get_template_configuration(self, template_manager):
        """Test getting configuration template"""
        template = template_manager.get_template(ChangeType.CONFIGURATION)
        
        assert template.title_prefix == "⚙️ Config:"
        assert "configuration" in template.labels
        assert "config" in template.labels
        assert "Rollback Plan" in template.description_template

    def test_get_template_tests(self, template_manager):
        """Test getting tests template"""
        template = template_manager.get_template(ChangeType.TESTS)
        
        assert template.title_prefix == "🧪 Tests:"
        assert "tests" in template.labels
        assert "testing" in template.labels

    def test_get_template_performance(self, template_manager):
        """Test getting performance template"""
        template = template_manager.get_template(ChangeType.PERFORMANCE)
        
        assert template.title_prefix == "⚡ Performance:"
        assert "performance" in template.labels
        assert "optimization" in template.labels
        assert "Benchmarks" in template.description_template

    def test_get_template_security(self, template_manager):
        """Test getting security template"""
        template = template_manager.get_template(ChangeType.SECURITY)
        
        assert template.title_prefix == "🔒 Security:"
        assert "security" in template.labels
        assert "vulnerability" in template.labels

    def test_detect_change_type_bugfix_description(self, template_manager):
        """Test change type detection from description keywords"""
        file_changes = [
            FileChange("src/main.py", "modified", 5, 3)
        ]
        
        # Test bug-related keywords
        assert template_manager.detect_change_type(file_changes, "Fix critical bug in authentication") == ChangeType.BUGFIX
        assert template_manager.detect_change_type(file_changes, "Resolve error in data processing") == ChangeType.BUGFIX
        assert template_manager.detect_change_type(file_changes, "Address issue with file uploads") == ChangeType.BUGFIX

    def test_detect_change_type_refactor_description(self, template_manager):
        """Test change type detection for refactoring"""
        file_changes = [
            FileChange("src/utils.py", "modified", 20, 15)
        ]
        
        assert template_manager.detect_change_type(file_changes, "Refactor database connection logic") == ChangeType.REFACTOR
        assert template_manager.detect_change_type(file_changes, "Cleanup old code and reorganize modules") == ChangeType.REFACTOR

    def test_detect_change_type_performance_description(self, template_manager):
        """Test change type detection for performance"""
        file_changes = [
            FileChange("src/api.py", "modified", 10, 5)
        ]
        
        assert template_manager.detect_change_type(file_changes, "Optimize database queries for speed") == ChangeType.PERFORMANCE
        assert template_manager.detect_change_type(file_changes, "Improve memory usage in data processing") == ChangeType.PERFORMANCE

    def test_detect_change_type_security_description(self, template_manager):
        """Test change type detection for security"""
        file_changes = [
            FileChange("src/auth.py", "modified", 8, 2)
        ]
        
        assert template_manager.detect_change_type(file_changes, "Fix security vulnerability in auth") == ChangeType.SECURITY
        assert template_manager.detect_change_type(file_changes, "Enhance authentication mechanisms") == ChangeType.SECURITY

    def test_detect_change_type_documentation_files(self, template_manager):
        """Test change type detection from documentation files"""
        file_changes = [
            FileChange("README.md", "modified", 10, 2),
            FileChange("docs/api.md", "added", 50, 0)
        ]
        
        assert template_manager.detect_change_type(file_changes, "Update API documentation") == ChangeType.DOCUMENTATION

    def test_detect_change_type_configuration_files(self, template_manager):
        """Test change type detection from configuration files"""
        file_changes = [
            FileChange("config.yml", "modified", 5, 1),
            FileChange("Dockerfile", "modified", 3, 2)
        ]
        
        assert template_manager.detect_change_type(file_changes, "Update deployment configuration") == ChangeType.CONFIGURATION

    def test_detect_change_type_test_files(self, template_manager):
        """Test change type detection from test files"""
        file_changes = [
            FileChange("tests/test_api.py", "added", 30, 0),
            FileChange("src/api.spec.js", "modified", 10, 5)
        ]
        
        assert template_manager.detect_change_type(file_changes, "Add comprehensive test coverage") == ChangeType.TESTS

    def test_detect_change_type_default_feature(self, template_manager):
        """Test default change type detection"""
        file_changes = [
            FileChange("src/new_feature.py", "added", 100, 0)
        ]
        
        assert template_manager.detect_change_type(file_changes, "Add new user management feature") == ChangeType.FEATURE

    def test_generate_pr_content_feature(self, template_manager):
        """Test PR content generation for feature"""
        content = template_manager.generate_pr_content(
            change_type=ChangeType.FEATURE,
            project_id="test-123",
            description="Add user authentication system",
            changes_summary="Added login, logout, and registration functionality",
            implementation_details="Implemented JWT-based authentication",
            timestamp="2023-01-01 12:00:00 UTC"
        )
        
        assert content['title'].startswith("✨ Feature:")
        assert "Add user authentication system" in content['title']
        assert "New Feature" in content['body']
        assert "Added login, logout, and registration functionality" in content['body']
        assert "Implemented JWT-based authentication" in content['body']
        assert "test-123" in content['body']
        assert "feature" in content['labels']
        assert "automated" in content['labels']
        assert "orb-generated" in content['labels']

    def test_generate_pr_content_bugfix(self, template_manager):
        """Test PR content generation for bugfix"""
        content = template_manager.generate_pr_content(
            change_type=ChangeType.BUGFIX,
            project_id="bug-456",
            description="Fix memory leak in data processor",
            changes_summary="Fixed object cleanup in processing loop",
            root_cause="Objects were not being properly garbage collected",
            solution_summary="Added explicit cleanup calls"
        )
        
        assert content['title'].startswith("🐛 Fix:")
        assert "Fix memory leak in data processor" in content['title']
        assert "Bug Fix" in content['body']
        assert "Objects were not being properly garbage collected" in content['body']
        assert "Added explicit cleanup calls" in content['body']
        assert "bugfix" in content['labels']

    def test_generate_pr_content_long_description(self, template_manager):
        """Test PR content generation with long description"""
        long_description = "This is a very long description that exceeds fifty characters and should be truncated in the title"
        
        content = template_manager.generate_pr_content(
            change_type=ChangeType.FEATURE,
            project_id="test-789",
            description=long_description,
            changes_summary="Multiple file changes"
        )
        
        # Title should be truncated
        assert len(content['title']) <= 60  # Prefix + 50 chars + "..."
        assert content['title'].endswith("...")
        
        # Full description should be in body
        assert long_description in content['body']

    def test_generate_pr_content_configuration_with_deployment_notes(self, template_manager):
        """Test PR content generation for configuration with deployment notes"""
        content = template_manager.generate_pr_content(
            change_type=ChangeType.CONFIGURATION,
            project_id="config-123",
            description="Update database connection settings",
            changes_summary="Modified connection pool settings",
            deployment_notes="Requires database restart",
            rollback_plan="Revert config file and restart services"
        )
        
        assert "Configuration Changes" in content['body']
        assert "Requires database restart" in content['body']
        assert "Revert config file and restart services" in content['body']
        assert "configuration" in content['labels']

    def test_generate_pr_content_performance_with_metrics(self, template_manager):
        """Test PR content generation for performance with metrics"""
        content = template_manager.generate_pr_content(
            change_type=ChangeType.PERFORMANCE,
            project_id="perf-456",
            description="Optimize API response times",
            changes_summary="Implemented query caching",
            before_metrics="Average response time: 500ms",
            after_metrics="Average response time: 150ms"
        )
        
        assert "Performance Improvement" in content['body']
        assert "Average response time: 500ms" in content['body']
        assert "Average response time: 150ms" in content['body']
        assert "performance" in content['labels']

    def test_generate_pr_content_checklist_items(self, template_manager):
        """Test that generated PR content includes checklist items"""
        content = template_manager.generate_pr_content(
            change_type=ChangeType.FEATURE,
            project_id="test-checklist",
            description="Test feature",
            changes_summary="Test changes"
        )
        
        # Should include checklist items from template
        assert "- [ ] Code follows project style guidelines" in content['body']
        assert "- [ ] Self-review completed" in content['body']
        assert "- [ ] Tests added for new functionality" in content['body']
        assert "- [ ] Documentation updated" in content['body']

    def test_generate_pr_content_automated_footer(self, template_manager):
        """Test that generated PR content includes automated footer"""
        content = template_manager.generate_pr_content(
            change_type=ChangeType.FEATURE,
            project_id="footer-test",
            description="Test automated footer",
            changes_summary="Test changes",
            timestamp="2023-01-01 12:00:00 UTC"
        )
        
        assert "Automated Information" in content['body']
        assert "footer-test" in content['body']
        assert "Orb AI Agent" in content['body']
        assert "2023-01-01 12:00:00 UTC" in content['body']
        assert "automatically generated by Orb" in content['body']