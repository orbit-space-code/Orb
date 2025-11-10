"""
Pull Request Templates
Provides templates for different types of changes
"""
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class ChangeType(Enum):
    """Types of changes for PR templates"""
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    TESTS = "tests"
    PERFORMANCE = "performance"
    SECURITY = "security"


@dataclass
class PRTemplate:
    """Pull request template data"""
    title_prefix: str
    description_template: str
    labels: List[str]
    checklist: List[str]


class PRTemplateManager:
    """Manages PR templates for different change types"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[ChangeType, PRTemplate]:
        """Initialize PR templates for different change types"""
        return {
            ChangeType.FEATURE: PRTemplate(
                title_prefix="✨ Feature:",
                description_template="""## 🚀 New Feature

### Description
{description}

### Changes Made
{changes_summary}

### Implementation Details
{implementation_details}

### Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

### Documentation
- [ ] Code comments added
- [ ] README updated (if needed)
- [ ] API documentation updated (if needed)
""",
                labels=["feature", "enhancement"],
                checklist=[
                    "Code follows project style guidelines",
                    "Self-review completed",
                    "Tests added for new functionality",
                    "Documentation updated"
                ]
            ),
            
            ChangeType.BUGFIX: PRTemplate(
                title_prefix="🐛 Fix:",
                description_template="""## 🔧 Bug Fix

### Problem Description
{description}

### Root Cause
{root_cause}

### Solution
{solution_summary}

### Changes Made
{changes_summary}

### Testing
- [ ] Bug reproduction test added
- [ ] Fix verified manually
- [ ] Regression tests pass
- [ ] No new issues introduced

### Impact
- [ ] Breaking changes: No
- [ ] Database changes: No
- [ ] Configuration changes: No
""",
                labels=["bugfix", "bug"],
                checklist=[
                    "Bug is reproducible",
                    "Root cause identified",
                    "Fix tested thoroughly",
                    "No regression introduced"
                ]
            ),
            
            ChangeType.REFACTOR: PRTemplate(
                title_prefix="♻️ Refactor:",
                description_template="""## 🔄 Code Refactoring

### Motivation
{description}

### Changes Made
{changes_summary}

### Benefits
- Improved code readability
- Better maintainability
- Enhanced performance (if applicable)
- Reduced technical debt

### Testing
- [ ] All existing tests pass
- [ ] No functional changes
- [ ] Performance impact assessed
- [ ] Code coverage maintained

### Verification
- [ ] Functionality unchanged
- [ ] API contracts preserved
- [ ] No breaking changes
""",
                labels=["refactor", "cleanup"],
                checklist=[
                    "No functional changes",
                    "All tests pass",
                    "Code quality improved",
                    "Performance not degraded"
                ]
            ),
            
            ChangeType.DOCUMENTATION: PRTemplate(
                title_prefix="📚 Docs:",
                description_template="""## 📖 Documentation Update

### Changes Made
{changes_summary}

### Motivation
{description}

### Documentation Type
- [ ] Code comments
- [ ] README updates
- [ ] API documentation
- [ ] User guides
- [ ] Developer guides

### Review Checklist
- [ ] Information is accurate
- [ ] Examples are working
- [ ] Links are valid
- [ ] Grammar and spelling checked
""",
                labels=["documentation", "docs"],
                checklist=[
                    "Information is accurate",
                    "Examples tested",
                    "Grammar checked",
                    "Links verified"
                ]
            ),
            
            ChangeType.CONFIGURATION: PRTemplate(
                title_prefix="⚙️ Config:",
                description_template="""## 🔧 Configuration Changes

### Changes Made
{changes_summary}

### Motivation
{description}

### Impact Assessment
- [ ] Development environment
- [ ] Testing environment
- [ ] Production environment
- [ ] CI/CD pipeline

### Deployment Notes
{deployment_notes}

### Rollback Plan
{rollback_plan}

### Testing
- [ ] Configuration validated
- [ ] Environment tested
- [ ] Deployment tested
""",
                labels=["configuration", "config"],
                checklist=[
                    "Configuration validated",
                    "Impact assessed",
                    "Rollback plan ready",
                    "Documentation updated"
                ]
            ),
            
            ChangeType.TESTS: PRTemplate(
                title_prefix="🧪 Tests:",
                description_template="""## 🔬 Test Updates

### Test Changes
{changes_summary}

### Coverage
- [ ] Unit tests
- [ ] Integration tests
- [ ] End-to-end tests
- [ ] Performance tests

### Motivation
{description}

### Test Results
- [ ] All tests pass
- [ ] Coverage maintained/improved
- [ ] No flaky tests introduced
- [ ] Test performance acceptable

### Quality Assurance
- [ ] Tests are deterministic
- [ ] Good test isolation
- [ ] Clear test descriptions
- [ ] Proper assertions
""",
                labels=["tests", "testing"],
                checklist=[
                    "All tests pass",
                    "Good test coverage",
                    "Tests are reliable",
                    "Clear test intent"
                ]
            ),
            
            ChangeType.PERFORMANCE: PRTemplate(
                title_prefix="⚡ Performance:",
                description_template="""## 🚀 Performance Improvement

### Performance Issue
{description}

### Changes Made
{changes_summary}

### Benchmarks
#### Before
{before_metrics}

#### After
{after_metrics}

### Impact
- [ ] Response time improved
- [ ] Memory usage optimized
- [ ] CPU usage reduced
- [ ] Database queries optimized

### Testing
- [ ] Performance tests added
- [ ] Load testing completed
- [ ] No functionality regression
- [ ] Memory leaks checked
""",
                labels=["performance", "optimization"],
                checklist=[
                    "Performance measured",
                    "Improvement verified",
                    "No regression",
                    "Tests updated"
                ]
            ),
            
            ChangeType.SECURITY: PRTemplate(
                title_prefix="🔒 Security:",
                description_template="""## 🛡️ Security Enhancement

### Security Issue
{description}

### Changes Made
{changes_summary}

### Security Impact
- [ ] Authentication improved
- [ ] Authorization enhanced
- [ ] Input validation added
- [ ] Data encryption improved
- [ ] Vulnerability patched

### Testing
- [ ] Security tests added
- [ ] Penetration testing (if applicable)
- [ ] Code review completed
- [ ] No new vulnerabilities introduced

### Compliance
- [ ] Security guidelines followed
- [ ] Audit trail maintained
- [ ] Documentation updated
""",
                labels=["security", "vulnerability"],
                checklist=[
                    "Security review completed",
                    "No new vulnerabilities",
                    "Compliance maintained",
                    "Documentation updated"
                ]
            )
        }
    
    def get_template(self, change_type: ChangeType) -> PRTemplate:
        """Get PR template for change type"""
        return self.templates.get(change_type, self.templates[ChangeType.FEATURE])
    
    def detect_change_type(self, file_changes: List[Any], description: str = "") -> ChangeType:
        """
        Detect change type based on file changes and description
        
        Args:
            file_changes: List of file changes
            description: Implementation description
            
        Returns:
            Detected change type
        """
        description_lower = description.lower()
        
        # Check description for keywords (order matters - more specific first)
        if any(word in description_lower for word in ['security', 'vulnerability', 'auth']):
            return ChangeType.SECURITY
        
        if any(word in description_lower for word in ['fix', 'bug', 'error', 'issue']):
            return ChangeType.BUGFIX
        
        if any(word in description_lower for word in ['refactor', 'cleanup', 'reorganize']):
            return ChangeType.REFACTOR
        
        if any(word in description_lower for word in ['performance', 'optimize', 'speed', 'memory']):
            return ChangeType.PERFORMANCE
        
        if any(word in description_lower for word in ['security', 'vulnerability', 'auth']):
            return ChangeType.SECURITY
        
        # Analyze file paths
        file_paths = [change.path.lower() for change in file_changes]
        
        # Configuration changes (check before documentation to avoid .yml/.json being caught as docs)
        config_patterns = ['config', '.env', '.yml', '.yaml', '.json', 'dockerfile']
        if any(pattern in path for path in file_paths for pattern in config_patterns):
            return ChangeType.CONFIGURATION
        
        # Documentation changes
        doc_patterns = ['readme', 'doc', '.md', 'documentation']
        if any(pattern in path for path in file_paths for pattern in doc_patterns):
            return ChangeType.DOCUMENTATION
        
        # Test changes
        test_patterns = ['test', 'spec', '__test__', '.test.', '.spec.']
        if any(pattern in path for path in file_paths for pattern in test_patterns):
            return ChangeType.TESTS
        
        # Default to feature
        return ChangeType.FEATURE
    
    def generate_pr_content(
        self,
        change_type: ChangeType,
        project_id: str,
        description: str,
        changes_summary: str,
        implementation_details: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate PR title and description using template
        
        Args:
            change_type: Type of change
            project_id: Project identifier
            description: Implementation description
            changes_summary: Summary of changes made
            implementation_details: Detailed implementation notes
            **kwargs: Additional template variables
            
        Returns:
            Dictionary with title, body, and labels
        """
        template = self.get_template(change_type)
        
        # Generate title (ensure total length doesn't exceed 60 chars)
        max_desc_length = 60 - len(template.title_prefix) - 4  # 4 for space and "..."
        if len(description) > max_desc_length:
            title = f"{template.title_prefix} {description[:max_desc_length]}..."
        else:
            title = f"{template.title_prefix} {description}"
        
        # Format description template
        template_vars = {
            'description': description,
            'changes_summary': changes_summary,
            'implementation_details': implementation_details or "Implementation completed by Orb AI agent.",
            'project_id': project_id,
            'root_cause': kwargs.get('root_cause', 'Identified during implementation'),
            'solution_summary': kwargs.get('solution_summary', changes_summary),
            'deployment_notes': kwargs.get('deployment_notes', 'Standard deployment process'),
            'rollback_plan': kwargs.get('rollback_plan', 'Revert commit if issues arise'),
            'before_metrics': kwargs.get('before_metrics', 'Baseline measurements taken'),
            'after_metrics': kwargs.get('after_metrics', 'Improvements measured')
        }
        
        body = template.description_template.format(**template_vars)
        
        # Add automated footer
        body += f"""

---

### 🤖 Automated Information
- **Project ID:** `{project_id}`
- **Generated by:** OrbitSpace AI Agent
- **Timestamp:** {kwargs.get('timestamp', 'N/A')}

### Review Checklist
"""
        
        for item in template.checklist:
            body += f"- [ ] {item}\n"
        
        body += "\n*This pull request was automatically generated by OrbitSpace AI coding assistant.*"
        
        return {
            'title': title,
            'body': body,
            'labels': template.labels + ['automated', 'orb-generated']
        }