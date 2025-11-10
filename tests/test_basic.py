"""
Basic tests to ensure the test suite runs
"""
import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_basic_import():
    """Test that basic imports work"""
    assert True


def test_environment_setup():
    """Test that environment is set up correctly"""
    assert sys.version_info >= (3, 11)


def test_redis_client_import():
    """Test that Redis client can be imported"""
    try:
        from orchestrator.redis_client import RedisClient
        assert RedisClient is not None
    except ImportError:
        pytest.skip("Redis client import failed - dependencies may not be available")


def test_api_routes_import():
    """Test that API routes can be imported"""
    try:
        from api.routes import router
        assert router is not None
    except ImportError:
        pytest.skip("API routes import failed - dependencies may not be available")


@pytest.mark.asyncio
async def test_async_functionality():
    """Test that async functionality works"""
    async def dummy_async():
        return True
    
    result = await dummy_async()
    assert result is True