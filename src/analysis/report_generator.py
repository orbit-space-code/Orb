"""
Report generation for analysis results
"""
import json
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from jinja2 import Template


class ReportGenerator:
    """Generate reports in various formats"""
    
    def __init__(self):
        self.html_template = self._get_html_template()
    
    def generate_json_report(
        self,
        analysis_results: Dict[str, Any],
        output_path: str,
    ) -> str:
        """Generate JSON report"""
        with open(output_path, 'w') as f:
            json.dump(analysis_results, f, indent=2)
        return output_path
    
    def generate_html_report(
        self,
        analysis_results: Dict[str, Any],
        output_path: str,
    ) -> str:
        """Generate HTML report"""
        html_content = self.html_template.render(
            results=analysis_results,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        return output_path
    
    def generate_markdown_report(
        self,
        analysis_results: Dict[str, Any],
        output_path: str,
    ) -> str:
        """Generate Markdown report"""
        summary = analysis_results.get("summary", {})
        issues = analysis_results.get("issues", [])
        tools = analysis_results.get("tools", [])
        
        md_content = f"""# Code Analysis Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Session ID:** {analysis_results.get("session_id", "N/A")}  
**Status:** {analysis_results.get("status", "N/A")}  
**Duration:** {analysis_results.get("duration_seconds", 0):.2f} seconds

---

## Summary

- **Total Issues:** {summary.get("total_issues", 0)}
- **Critical Issues:** {summary.get("critical_issues", 0)}
- **High Issues:** {summary.get("high_issues", 0)}
- **Medium Issues:** {summary.get("medium_issues", 0)}
- **Low Issues:** {summary.get("low_issues", 0)}
- **Files Analyzed:** {summary.get("files_analyzed", 0)}
- **Lines Analyzed:** {summary.get("lines_analyzed", 0)}

---

## Issues by Category

- **Security:** {summary.get("security_issues", 0)}
- **Bugs:** {summary.get("bug_issues", 0)}
- **Code Smells:** {summary.get("code_smell_issues", 0)}
- **Style:** {summary.get("style_issues", 0)}

---

## Tools Executed

"""
        
        for tool in tools:
            md_content += f"""
### {tool['name']} (v{tool['version']})
- **Status:** {tool['status']}
- **Issues Found:** {tool['issues_found']}
- **Execution Time:** {tool['execution_time_ms']}ms
"""
        
        md_content += "\n---\n\n## Issues\n\n"
        
        # Group issues by severity
        issues_by_severity = {}
        for issue in issues:
            severity = issue.get("severity", "info")
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            issues_by_severity[severity].append(issue)
        
        for severity in ["critical", "high", "medium", "low", "info"]:
            if severity in issues_by_severity:
                md_content += f"\n### {severity.upper()} Issues\n\n"
                for issue in issues_by_severity[severity]:
                    md_content += f"""
**{issue.get('rule_id', 'unknown')}** - {issue.get('file_path', 'unknown')}:{issue.get('line_number', '?')}  
{issue.get('message', '')}
"""
                    if issue.get('suggestion'):
                        md_content += f"*Suggestion:* {issue['suggestion']}\n"
                    md_content += "\n"
        
        with open(output_path, 'w') as f:
            f.write(md_content)
        return output_path
    
    def generate_executive_summary(
        self,
        analysis_results: Dict[str, Any],
    ) -> str:
        """Generate executive summary text"""
        summary = analysis_results.get("summary", {})
        status = analysis_results.get("status", "unknown")
        
        total_issues = summary.get("total_issues", 0)
        critical = summary.get("critical_issues", 0)
        high = summary.get("high_issues", 0)
        security = summary.get("security_issues", 0)
        
        if status == "passed":
            return "✅ No issues found. Code quality is excellent."
        
        summary_text = f"Found {total_issues} issues in the codebase. "
        
        if critical > 0:
            summary_text += f"⚠️ {critical} CRITICAL issues require immediate attention. "
        
        if high > 0:
            summary_text += f"{high} HIGH priority issues should be addressed soon. "
        
        if security > 0:
            summary_text += f"🔒 {security} security vulnerabilities detected. "
        
        return summary_text
    
    def _get_html_template(self) -> Template:
        """Get HTML template for reports"""
        template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Analysis Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
        }
        .critical { color: #dc2626; }
        .high { color: #ea580c; }
        .medium { color: #f59e0b; }
        .low { color: #3b82f6; }
        .info { color: #6b7280; }
        .issues-table {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #f9fafb;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e5e7eb;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }
        .severity-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .badge-critical { background: #fee2e2; color: #dc2626; }
        .badge-high { background: #ffedd5; color: #ea580c; }
        .badge-medium { background: #fef3c7; color: #f59e0b; }
        .badge-low { background: #dbeafe; color: #3b82f6; }
        .badge-info { background: #f3f4f6; color: #6b7280; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Code Analysis Report</h1>
        <p>Generated: {{ generated_at }}</p>
        <p>Session ID: {{ results.session_id }}</p>
        <p>Status: {{ results.status }}</p>
    </div>
    
    <div class="summary">
        <div class="stat-card">
            <div class="stat-label">Total Issues</div>
            <div class="stat-value">{{ results.summary.total_issues }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Critical</div>
            <div class="stat-value critical">{{ results.summary.critical_issues }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">High</div>
            <div class="stat-value high">{{ results.summary.high_issues }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Medium</div>
            <div class="stat-value medium">{{ results.summary.medium_issues }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Files Analyzed</div>
            <div class="stat-value">{{ results.summary.files_analyzed }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Lines Analyzed</div>
            <div class="stat-value">{{ results.summary.lines_analyzed }}</div>
        </div>
    </div>
    
    <div class="issues-table">
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>File</th>
                    <th>Line</th>
                    <th>Rule</th>
                    <th>Message</th>
                </tr>
            </thead>
            <tbody>
                {% for issue in results.issues %}
                <tr>
                    <td>
                        <span class="severity-badge badge-{{ issue.severity }}">
                            {{ issue.severity }}
                        </span>
                    </td>
                    <td>{{ issue.file_path }}</td>
                    <td>{{ issue.line_number or '-' }}</td>
                    <td><code>{{ issue.rule_id }}</code></td>
                    <td>{{ issue.message }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        return Template(template_str)
