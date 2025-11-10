"""
Code refactoring tool for automated code improvements
"""
import os
import ast
import re
from typing import Dict, Any, List
from src.tools.registry import Tool


class RefactorTool(Tool):
    """Automated code refactoring tool"""
    
    def __init__(self):
        super().__init__(
            name="refactor",
            description="Perform automated code refactoring operations"
        )
    
    async def execute(
        self,
        workspace_path: str,
        operation: str,
        target_file: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform refactoring
        
        Args:
            workspace_path: Path to workspace
            operation: Refactoring operation (extract_function, rename, inline, etc.)
            target_file: File to refactor
            **kwargs: Operation-specific parameters
        """
        file_path = os.path.join(workspace_path, target_file)
        
        if not os.path.exists(file_path):
            return {"error": f"File not found: {target_file}"}
        
        if operation == "extract_function":
            return await self._extract_function(file_path, **kwargs)
        elif operation == "rename":
            return await self._rename(file_path, **kwargs)
        elif operation == "remove_dead_code":
            return await self._remove_dead_code(file_path)
        elif operation == "simplify_conditionals":
            return await self._simplify_conditionals(file_path)
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    async def _extract_function(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        function_name: str,
    ) -> Dict[str, Any]:
        """Extract code block into a new function"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Extract the code block
            extracted_lines = lines[start_line-1:end_line]
            extracted_code = ''.join(extracted_lines)
            
            # Determine indentation
            indent = len(extracted_lines[0]) - len(extracted_lines[0].lstrip())
            base_indent = ' ' * indent
            
            # Create new function
            new_function = f"\n{base_indent}def {function_name}():\n"
            for line in extracted_lines:
                new_function += f"{base_indent}    {line.lstrip()}"
            new_function += "\n"
            
            # Replace original code with function call
            function_call = f"{base_indent}{function_name}()\n"
            
            # Build new file content
            new_lines = (
                lines[:start_line-1] +
                [function_call] +
                lines[end_line:]
            )
            
            # Insert function definition before the class/function containing the code
            # For simplicity, insert at the beginning of the file
            new_lines = [new_function] + new_lines
            
            # Write back
            with open(file_path, 'w') as f:
                f.writelines(new_lines)
            
            return {
                "success": True,
                "operation": "extract_function",
                "function_name": function_name,
                "lines_extracted": end_line - start_line + 1,
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    async def _rename(
        self,
        file_path: str,
        old_name: str,
        new_name: str,
        scope: str = "file",
    ) -> Dict[str, Any]:
        """Rename a variable, function, or class"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(old_name) + r'\b'
            new_content = re.sub(pattern, new_name, content)
            
            # Count replacements
            replacements = content.count(old_name) - new_content.count(old_name)
            
            with open(file_path, 'w') as f:
                f.write(new_content)
            
            return {
                "success": True,
                "operation": "rename",
                "old_name": old_name,
                "new_name": new_name,
                "replacements": replacements,
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    async def _remove_dead_code(self, file_path: str) -> Dict[str, Any]:
        """Remove unused imports and variables"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Find all imports
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
            
            # Find all names used in the code
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
            
            # Find unused imports
            unused_imports = imports - used_names
            
            # Remove unused imports from content
            lines = content.splitlines()
            new_lines = []
            removed_count = 0
            
            for line in lines:
                is_unused = False
                for unused in unused_imports:
                    if f"import {unused}" in line or f"from {unused}" in line:
                        is_unused = True
                        removed_count += 1
                        break
                
                if not is_unused:
                    new_lines.append(line)
            
            new_content = '\n'.join(new_lines)
            
            with open(file_path, 'w') as f:
                f.write(new_content)
            
            return {
                "success": True,
                "operation": "remove_dead_code",
                "unused_imports": list(unused_imports),
                "lines_removed": removed_count,
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    async def _simplify_conditionals(self, file_path: str) -> Dict[str, Any]:
        """Simplify complex conditional statements"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Simple patterns to simplify
            simplifications = [
                (r'if\s+(\w+)\s*==\s*True:', r'if \1:'),
                (r'if\s+(\w+)\s*==\s*False:', r'if not \1:'),
                (r'if\s+not\s+(\w+)\s*==\s*True:', r'if not \1:'),
                (r'if\s+not\s+(\w+)\s*==\s*False:', r'if \1:'),
            ]
            
            new_content = content
            changes = 0
            
            for pattern, replacement in simplifications:
                matches = len(re.findall(pattern, new_content))
                new_content = re.sub(pattern, replacement, new_content)
                changes += matches
            
            if changes > 0:
                with open(file_path, 'w') as f:
                    f.write(new_content)
            
            return {
                "success": True,
                "operation": "simplify_conditionals",
                "simplifications": changes,
            }
        
        except Exception as e:
            return {"error": str(e)}
