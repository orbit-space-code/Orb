"""
Test generation tool for creating unit tests
"""
import os
import ast
from typing import Dict, Any, List
from src.tools.registry import Tool


class TestGeneratorTool(Tool):
    """Generate unit tests for code"""
    
    def __init__(self):
        super().__init__(
            name="test_generator",
            description="Generate unit tests for functions and classes"
        )
    
    async def execute(
        self,
        workspace_path: str,
        target_file: str,
        test_framework: str = "pytest",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate tests
        
        Args:
            workspace_path: Path to workspace
            target_file: File to generate tests for
            test_framework: Testing framework (pytest, unittest)
        """
        file_path = os.path.join(workspace_path, target_file)
        
        if not os.path.exists(file_path):
            return {"error": f"File not found: {target_file}"}
        
        if test_framework == "pytest":
            return await self._generate_pytest(file_path, target_file)
        elif test_framework == "unittest":
            return await self._generate_unittest(file_path, target_file)
        else:
            return {"error": f"Unknown framework: {test_framework}"}
    
    async def _generate_pytest(self, file_path: str, target_file: str) -> Dict[str, Any]:
        """Generate pytest tests"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Extract functions and classes
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                    functions.append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "line": node.lineno,
                    })
                elif isinstance(node, ast.ClassDef):
                    methods = [
                        n.name for n in node.body
                        if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')
                    ]
                    classes.append({
                        "name": node.name,
                        "methods": methods,
                        "line": node.lineno,
                    })
            
            # Generate test file content
            test_content = self._build_pytest_content(target_file, functions, classes)
            
            # Determine test file path
            test_file_name = f"test_{os.path.basename(target_file)}"
            test_dir = os.path.join(os.path.dirname(file_path), "tests")
            os.makedirs(test_dir, exist_ok=True)
            test_file_path = os.path.join(test_dir, test_file_name)
            
            # Write test file
            with open(test_file_path, 'w') as f:
                f.write(test_content)
            
            return {
                "success": True,
                "test_file": test_file_path,
                "functions_tested": len(functions),
                "classes_tested": len(classes),
                "total_tests": len(functions) + sum(len(c["methods"]) for c in classes),
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    def _build_pytest_content(
        self,
        target_file: str,
        functions: List[Dict],
        classes: List[Dict],
    ) -> str:
        """Build pytest test file content"""
        module_name = os.path.splitext(os.path.basename(target_file))[0]
        
        content = f'''"""
Tests for {target_file}
"""
import pytest
from {module_name} import *


'''
        
        # Generate tests for functions
        for func in functions:
            func_name = func["name"]
            args = func["args"]
            
            content += f'''def test_{func_name}():
    """Test {func_name} function"""
    # TODO: Add test implementation
'''
            
            if args:
                content += f"    # Function parameters: {', '.join(args)}\n"
            
            content += "    pass\n\n\n"
        
        # Generate tests for classes
        for cls in classes:
            cls_name = cls["name"]
            
            content += f'''class Test{cls_name}:
    """Tests for {cls_name} class"""
    
    @pytest.fixture
    def instance(self):
        """Create instance for testing"""
        return {cls_name}()
    
'''
            
            for method in cls["methods"]:
                content += f'''    def test_{method}(self, instance):
        """Test {method} method"""
        # TODO: Add test implementation
        pass
    
'''
        
        return content
    
    async def _generate_unittest(self, file_path: str, target_file: str) -> Dict[str, Any]:
        """Generate unittest tests"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Extract functions and classes
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    methods = [
                        n.name for n in node.body
                        if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')
                    ]
                    classes.append({"name": node.name, "methods": methods})
            
            # Generate test file content
            module_name = os.path.splitext(os.path.basename(target_file))[0]
            
            content = f'''"""
Tests for {target_file}
"""
import unittest
from {module_name} import *


'''
            
            # Generate test class
            content += f'''class Test{module_name.capitalize()}(unittest.TestCase):
    """Test cases for {module_name}"""
    
    def setUp(self):
        """Set up test fixtures"""
        pass
    
    def tearDown(self):
        """Clean up after tests"""
        pass
    
'''
            
            # Generate test methods for functions
            for func in functions:
                content += f'''    def test_{func}(self):
        """Test {func} function"""
        # TODO: Add test implementation
        self.assertTrue(True)
    
'''
            
            # Generate test methods for class methods
            for cls in classes:
                for method in cls["methods"]:
                    content += f'''    def test_{cls["name"]}_{method}(self):
        """Test {cls["name"]}.{method} method"""
        # TODO: Add test implementation
        self.assertTrue(True)
    
'''
            
            content += '''

if __name__ == '__main__':
    unittest.main()
'''
            
            # Write test file
            test_file_name = f"test_{os.path.basename(target_file)}"
            test_dir = os.path.join(os.path.dirname(file_path), "tests")
            os.makedirs(test_dir, exist_ok=True)
            test_file_path = os.path.join(test_dir, test_file_name)
            
            with open(test_file_path, 'w') as f:
                f.write(content)
            
            return {
                "success": True,
                "test_file": test_file_path,
                "functions_tested": len(functions),
                "classes_tested": len(classes),
            }
        
        except Exception as e:
            return {"error": str(e)}
