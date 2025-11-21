"""
Pytest configuration file.
Sets up the Python path and environment for running tests.
"""
import sys
import os
from pathlib import Path

# Set environment variables for testing BEFORE importing any modules
os.environ.setdefault('OPENAI_API_KEY', 'sk-fake-test-key-for-pytest-testing-only')
os.environ.setdefault('OPENAI_BASE_URL', 'https://api.openai.com/v1')
os.environ.setdefault('AI_MODEL', 'gpt-3.5-turbo')
os.environ.setdefault('DEBUG', 'False')

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

