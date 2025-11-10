"""
GitHub Pull Request Labeling System
Handles automatic label assignment based on change types and project lifecycle
"""
import re
import logging
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass
from enum import Enum
from .pull_request_service import FileChange

logger = logging.getLogger(__name__)


class LabelCategory(Enum):
    """Categories of PR labels"""
    TYPE = "type"           # type: feature, bugfix, refactor, etc.
    SCOPE = "scope"         # scope: frontend, backend, database, etc.
    PRIORITY = "priority"   # priority: high, medium, low
    SIZE = "size"           # size: xs, s, m, l, xl
    STATUS = "status"       # status: draft, ready, blocked, etc.
    AUTOMATION = "automation"  # automation: orbitspace, ai-generated


@dataclass
class LabelRule:
    """Rule for automatic label assignment"""
    name: str
    color: str
    description: str
    category: LabelCategory
    conditions: List[str]  # Conditions that trigger this label
    priority: int = 0      # Higher priority labels override lower ones


class PRLabelingService:
    """
    Service for automatic PR labeling based on change analysis
    Real implementation without mock data
    """

    def __init__(self):
        self.label_rules = self._initialize_label_rules()
        self.size_thresholds = {
            'xs': (0, 10),      # 0-10 lines changed
            's': (11, 50),      # 11-50 lines changed
            'm': (51, 200),     # 51-200 lines changed
            'l': (201, 500),    # 201-500 lines changed
            'xl': (501, float('inf'))  # 500+ lines changed
        }

    def _initialize_label_rules(self) -> List[LabelRule]:
        """Initialize comprehensive label rules for OrbitSpace"""
        return [
            # Type labels
            LabelRule(
                name="type: feature",
                color="0e8a16",
                description="New feature implementation",
                category=LabelCategory.TYPE,
                conditions=["new_files", "enhancement", "feature_keywords"],
                priority=10
            ),
            LabelRule(
                name="type: bugfix",
                color="d73a49",
                description="Bug fix or error correction",
                category=LabelCategory.TYPE,
                conditions=["fix_keywords", "error_keywords", "bug_keywords"],
                priority=15
            ),
            LabelRule(
                name="type: refactor",
                color="fbca04",
                description="Code refactoring without functional changes",
                category=LabelCategory.TYPE,
                conditions=["refactor_keywords", "cleanup_keywords", "no_new_features"],
                priority=12
            ),
            LabelRule(
                name="type: documentation",
                color="0075ca",
                description="Documentation updates",
                category=LabelCategory.TYPE,
                conditions=["doc_files", "readme_files", "doc_keywords"],
                priority=8
            ),
            LabelRule(
                name="type: configuration",
                color="5319e7",
                description="Configuration or setup changes",
                category=LabelCategory.TYPE,
                conditions=["config_files", "env_files", "docker_files"],
                priority=9
            ),
            LabelRule(
                name="type: tests",
                color="1d76db",
                description="Test additions or modifications",
                category=LabelCategory.TYPE,
                conditions=["test_files", "spec_files", "test_keywords"],
                priority=7
            ),
            LabelRule(
                name="type: performance",
                color="ff6b35",
                description="Performance improvements",
                category=LabelCategory.TYPE,
                conditions=["performance_keywords", "optimization_keywords"],
                priority=13
            ),
            LabelRule(
                name="type: security",
                color="b60205",
                description="Security enhancements or fixes",
                category=LabelCategory.TYPE,
                conditions=["security_keywords", "auth_files", "vulnerability_keywords"],
                priority=20
            ),

            # Scope labels
            LabelRule(
                name="scope: frontend",
                color="e99695",
                description="Frontend/UI changes",
                category=LabelCategory.SCOPE,
                conditions=["frontend_files", "ui_files", "component_files"],
                priority=5
            ),
            LabelRule(
                name="scope: backend",
                color="c2e0c6",
                description="Backend/API changes",
                category=LabelCategory.SCOPE,
                conditions=["backend_files", "api_files", "server_files"],
                priority=5
            ),
            LabelRule(
                name="scope: database",
                color="d4c5f9",
                description="Database schema or query changes",
                category=LabelCategory.SCOPE,
                conditions=["db_files", "migration_files", "schema_files"],
                priority=6
            ),
            LabelRule(
                name="scope: infrastructure",
                color="f9d0c4",
                description="Infrastructure or deployment changes",
                category=LabelCategory.SCOPE,
                conditions=["infra_files", "deploy_files", "ci_files"],
                priority=6
            ),

            # Priority labels
            LabelRule(
                name="priority: high",
                color="d73a49",
                description="High priority changes",
                category=LabelCategory.PRIORITY,
                conditions=["security_keywords", "critical_keywords", "urgent_keywords"],
                priority=18
            ),
            LabelRule(
                name="priority: medium",
                color="fbca04",
                description="Medium priority changes",
                category=LabelCategory.PRIORITY,
                conditions=["important_keywords", "feature_keywords"],
                priority=3
            ),
            LabelRule(
                name="priority: low",
                color="0e8a16",
                description="Low priority changes",
                category=LabelCategory.PRIORITY,
                conditions=["cleanup_keywords", "doc_keywords"],
                priority=2
            ),

            # Status labels
            LabelRule(
                name="status: draft",
                color="6f42c1",
                description="Work in progress",
                category=LabelCategory.STATUS,
                conditions=["is_draft"],
                priority=1
            ),
            LabelRule(
                name="status: ready",
                color="0e8a16",
                description="Ready for review",
                category=LabelCategory.STATUS,
                conditions=["not_draft", "complete_implementation"],
                priority=1
            ),

            # Automation labels
            LabelRule(
                name="orbitspace: ai-generated",
                color="7057ff",
                description="Generated by OrbitSpace AI",
                category=LabelCategory.AUTOMATION,
                conditions=["always"],  # Always applied for OrbitSpace PRs
                priority=25
            ),
            LabelRule(
                name="orbitspace: automated",
                color="5a32a3",
                description="Automated pull request",
                category=LabelCategory.AUTOMATION,
                conditions=["always"],  # Always applied for OrbitSpace PRs
                priority=24
            )
        ]

    def analyze_and_label_pr(
        self,
        file_changes: List[FileChange],
        pr_title: str,
        pr_description: str,
        is_draft: bool = False,
        project_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Analyze PR and determine appropriate labels
        
        Args:
            file_changes: List of file changes in the PR
            pr_title: PR title
            pr_description: PR description
            is_draft: Whether PR is in draft state
            project_context: Additional project context
            
        Returns:
            List of label names to apply
        """
        try:
            logger.info(f"Analyzing PR for labeling: {len(file_changes)} file changes")
            
            # Analyze file changes
            change_analysis = self._analyze_file_changes(file_changes)
            
            # Analyze text content
            text_analysis = self._analyze_text_content(pr_title, pr_description)
            
            # Determine size
            size_analysis = self._analyze_pr_size(file_changes)
            
            # Combine all analysis
            conditions = {
                **change_analysis,
                **text_analysis,
                **size_analysis,
                'is_draft': is_draft,
                'not_draft': not is_draft,
                'always': True
            }
            
            # Apply project context if available
            if project_context:
                conditions.update(self._analyze_project_context(project_context))
            
            # Determine labels based on rules
            applicable_labels = []
            for rule in self.label_rules:
                if self._rule_matches(rule, conditions):
                    applicable_labels.append((rule.name, rule.priority))
            
            # Sort by priority and remove duplicates
            applicable_labels.sort(key=lambda x: x[1], reverse=True)
            final_labels = [label[0] for label in applicable_labels]
            
            # Add size label
            size_label = self._get_size_label(file_changes)
            if size_label:
                final_labels.append(size_label)
            
            logger.info(f"Generated {len(final_labels)} labels for PR")
            return final_labels
            
        except Exception as e:
            logger.error(f"Failed to analyze PR for labeling: {e}")
            # Return basic labels as fallback
            return ["orbitspace: ai-generated", "orbitspace: automated"]

    def _analyze_file_changes(self, file_changes: List[FileChange]) -> Dict[str, bool]:
        """Analyze file changes to determine conditions"""
        conditions = {}
        
        file_paths = [change.path.lower() for change in file_changes]
        file_extensions = set()
        
        for change in file_changes:
            if '.' in change.path:
                ext = change.path.split('.')[-1].lower()
                file_extensions.add(ext)
        
        # File type analysis
        conditions['frontend_files'] = any(
            ext in ['tsx', 'jsx', 'vue', 'html', 'css', 'scss', 'sass'] 
            for ext in file_extensions
        ) or any('component' in path for path in file_paths)
        
        conditions['backend_files'] = any(
            ext in ['py', 'js', 'ts', 'java', 'go', 'rs'] 
            for ext in file_extensions
        ) or any(path.startswith('src/api') or path.startswith('api/') for path in file_paths)
        
        conditions['db_files'] = any(
            'migration' in path or 'schema' in path or 'prisma' in path 
            for path in file_paths
        ) or any(ext in ['sql'] for ext in file_extensions)
        
        conditions['config_files'] = any(
            ext in ['json', 'yml', 'yaml', 'toml', 'ini'] 
            for ext in file_extensions
        ) or any('config' in path for path in file_paths)
        
        conditions['test_files'] = any(
            'test' in path or 'spec' in path or '__test__' in path 
            for path in file_paths
        )
        
        conditions['doc_files'] = any(
            ext in ['md', 'rst', 'txt'] for ext in file_extensions
        ) or any('doc' in path or 'readme' in path for path in file_paths)
        
        conditions['docker_files'] = any(
            'dockerfile' in path or 'docker-compose' in path 
            for path in file_paths
        )
        
        conditions['ci_files'] = any(
            '.github' in path or '.gitlab' in path or 'ci' in path 
            for path in file_paths
        )
        
        # Change type analysis
        conditions['new_files'] = any(change.status == 'added' for change in file_changes)
        conditions['deleted_files'] = any(change.status == 'deleted' for change in file_changes)
        conditions['modified_files'] = any(change.status == 'modified' for change in file_changes)
        
        return conditions

    def _analyze_text_content(self, title: str, description: str) -> Dict[str, bool]:
        """Analyze PR title and description for keywords"""
        text = f"{title} {description}".lower()
        
        return {
            'feature_keywords': any(word in text for word in [
                'feature', 'add', 'implement', 'create', 'new', 'enhancement'
            ]),
            'fix_keywords': any(word in text for word in [
                'fix', 'bug', 'error', 'issue', 'problem', 'resolve'
            ]),
            'refactor_keywords': any(word in text for word in [
                'refactor', 'cleanup', 'reorganize', 'restructure', 'improve'
            ]),
            'performance_keywords': any(word in text for word in [
                'performance', 'optimize', 'speed', 'faster', 'efficiency', 'memory'
            ]),
            'security_keywords': any(word in text for word in [
                'security', 'vulnerability', 'auth', 'authentication', 'authorization'
            ]),
            'doc_keywords': any(word in text for word in [
                'documentation', 'readme', 'docs', 'guide', 'manual'
            ]),
            'test_keywords': any(word in text for word in [
                'test', 'testing', 'spec', 'coverage', 'unit test', 'integration test'
            ]),
            'critical_keywords': any(word in text for word in [
                'critical', 'urgent', 'hotfix', 'emergency', 'breaking'
            ]),
            'important_keywords': any(word in text for word in [
                'important', 'significant', 'major', 'key'
            ])
        }

    def _analyze_pr_size(self, file_changes: List[FileChange]) -> Dict[str, bool]:
        """Analyze PR size based on line changes"""
        total_changes = sum(change.additions + change.deletions for change in file_changes)
        file_count = len(file_changes)
        
        return {
            'small_pr': total_changes <= 50 and file_count <= 3,
            'medium_pr': 50 < total_changes <= 200 and file_count <= 10,
            'large_pr': total_changes > 200 or file_count > 10,
            'massive_pr': total_changes > 500 or file_count > 20
        }

    def _analyze_project_context(self, context: Dict[str, Any]) -> Dict[str, bool]:
        """Analyze project context for additional conditions"""
        conditions = {}
        
        # Project phase context
        phase = context.get('phase', '').lower()
        conditions['research_phase'] = phase == 'research'
        conditions['planning_phase'] = phase == 'planning'
        conditions['implementation_phase'] = phase == 'implementation'
        
        # Project type context
        project_type = context.get('type', '').lower()
        conditions['web_project'] = 'web' in project_type
        conditions['api_project'] = 'api' in project_type
        conditions['mobile_project'] = 'mobile' in project_type
        
        return conditions

    def _rule_matches(self, rule: LabelRule, conditions: Dict[str, bool]) -> bool:
        """Check if a label rule matches the current conditions"""
        for condition in rule.conditions:
            if conditions.get(condition, False):
                return True
        return False

    def _get_size_label(self, file_changes: List[FileChange]) -> Optional[str]:
        """Get size label based on total line changes"""
        total_changes = sum(change.additions + change.deletions for change in file_changes)
        
        for size, (min_changes, max_changes) in self.size_thresholds.items():
            if min_changes <= total_changes <= max_changes:
                return f"size: {size}"
        
        return "size: xl"  # Fallback for very large changes

    def create_label_definitions(self) -> List[Dict[str, str]]:
        """
        Create label definitions for GitHub repository setup
        
        Returns:
            List of label definitions with name, color, and description
        """
        return [
            {
                'name': rule.name,
                'color': rule.color,
                'description': rule.description
            }
            for rule in self.label_rules
        ] + [
            # Size labels
            {'name': 'size: xs', 'color': 'c5def5', 'description': 'Extra small changes (0-10 lines)'},
            {'name': 'size: s', 'color': 'bfd4f2', 'description': 'Small changes (11-50 lines)'},
            {'name': 'size: m', 'color': 'a8c8ec', 'description': 'Medium changes (51-200 lines)'},
            {'name': 'size: l', 'color': '91bce6', 'description': 'Large changes (201-500 lines)'},
            {'name': 'size: xl', 'color': '7ab0e0', 'description': 'Extra large changes (500+ lines)'},
        ]

    def get_recommended_reviewers(
        self, 
        file_changes: List[FileChange], 
        project_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Get recommended reviewers based on file changes
        
        Args:
            file_changes: List of file changes
            project_context: Project context information
            
        Returns:
            List of recommended reviewer usernames
        """
        # This would typically integrate with team structure
        # For now, return based on change types
        reviewers = set()
        
        change_analysis = self._analyze_file_changes(file_changes)
        
        if change_analysis.get('frontend_files'):
            reviewers.add('frontend-team')
        
        if change_analysis.get('backend_files'):
            reviewers.add('backend-team')
        
        if change_analysis.get('db_files'):
            reviewers.add('database-team')
        
        if change_analysis.get('security_keywords'):
            reviewers.add('security-team')
        
        # Always add AI review for OrbitSpace generated PRs
        reviewers.add('orbitspace-ai-review')
        
        return list(reviewers)