#!/usr/bin/env python3
"""
Script to remove all OrbitSpace references from the codebase.
Replaces them with 'OrbitSpace' or 'Orb' as appropriate.
"""
import os
import re
from pathlib import Path
from typing import List, Tuple

# Base directory of the project
BASE_DIR = Path(__file__).parent.parent

# Files to exclude from processing
EXCLUDE_DIRS = {
    '.git',
    'node_modules',
    '__pycache__',
    '.next',
    '.vercel',
    'venv',
    'env',
    '.idea',
    '.vscode',
}

# File patterns to include
INCLUDE_PATTERNS = {
    '*.py', '*.md', '*.ts', '*.tsx', '*.js', '*.jsx', '*.json', '*.yml', '*.yaml',
    'Dockerfile*', 'docker-compose*.yml', '*.sh', '*.txt'
}

# Replacement mappings
REPLACEMENTS = {
    # Case-insensitive replacements
    r'(?i)OrbitSpace\.ai': 'OrbitSpace',
    r'(?i)OrbitSpace\.dev': 'orbitspace.dev',
    r'(?i)OrbitSpace': 'OrbitSpace',
    # Specific case-sensitive replacements
    'OrbitSpace/': 'orb-',  # For branch names
    'OrbitSpace Bot': 'OrbitSpace Bot',
    'bot@orbitspace.dev': 'bot@orbitspace.dev',
    'orbitspace_OrbitSpace': 'orbitspace',
    'orbitspace-OrbitSpace': 'orbitspace',
}

def should_process_file(file_path: Path) -> bool:
    """Check if a file should be processed."""
    # Skip excluded directories
    for part in file_path.parts:
        if part in EXCLUDE_DIRS:
            return False
    
    # Check file extension
    return any(file_path.match(pattern) for pattern in INCLUDE_PATTERNS)

def process_file(file_path: Path):
    """Process a single file to replace OrbitSpace references."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all replacements
        for pattern, replacement in REPLACEMENTS.items():
            content = re.sub(pattern, replacement, content)
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path.relative_to(BASE_DIR)}")
            
    except UnicodeDecodeError:
        print(f"Skipping binary file: {file_path.relative_to(BASE_DIR)}")
    except Exception as e:
        print(f"Error processing {file_path.relative_to(BASE_DIR)}: {str(e)}")

def main():
    print("Removing OrbitSpace references...")
    
    # Process all files in the project directory
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            file_path = Path(root) / file
            if should_process_file(file_path):
                process_file(file_path)
    
    print("\nDone! All OrbitSpace references have been removed.")
    print("Please review the changes before committing.")

if __name__ == "__main__":
    main()
