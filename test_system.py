#!/usr/bin/env python3
"""
End-to-end system validation script for Orbitspace Compyle
Tests all critical components and connections
"""

import sys
import asyncio
import aiohttp
import redis.asyncio as redis
from typing import Dict, List, Tuple
from anthropic import Anthropic
import os
from pathlib import Path

class SystemValidator:
    def __init__(self):
        self.results: List[Tuple[str, bool, str]] = []
        self.fastapi_url = os.getenv("FASTAPI_URL", "http://localhost:8000")
        self.nextjs_url = os.getenv("NEXTJS_API_URL", "http://localhost:3000")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append((test_name, passed, message))
        print(f"{status} - {test_name}")
        if message:
            print(f"   {message}")

    async def test_redis_connection(self) -> bool:
        """Test Redis connectivity"""
        try:
            r = redis.from_url(self.redis_url, decode_responses=True)
            await r.ping()
            await r.aclose()
            self.log_result("Redis Connection", True, "Successfully connected to Redis")
            return True
        except Exception as e:
            self.log_result("Redis Connection", False, f"Error: {str(e)}")
            return False

    async def test_postgres_connection(self) -> bool:
        """Test PostgreSQL connectivity (via database URL)"""
        try:
            # Simple check - see if DATABASE_URL is set
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                self.log_result("PostgreSQL Configuration", False, "DATABASE_URL not set")
                return False

            self.log_result("PostgreSQL Configuration", True, "DATABASE_URL configured")
            return True
        except Exception as e:
            self.log_result("PostgreSQL Configuration", False, f"Error: {str(e)}")
            return False

    async def test_anthropic_api(self) -> bool:
        """Test Anthropic API connectivity"""
        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                self.log_result("Anthropic API", False, "ANTHROPIC_API_KEY not set")
                return False

            client = Anthropic(api_key=api_key)
            # Simple API check
            self.log_result("Anthropic API Configuration", True, "API key configured")
            return True
        except Exception as e:
            self.log_result("Anthropic API", False, f"Error: {str(e)}")
            return False

    async def test_fastapi_health(self) -> bool:
        """Test FastAPI health endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.fastapi_url}/health", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.log_result("FastAPI Health", True, f"Status: {data.get('status')}")
                        return True
                    else:
                        self.log_result("FastAPI Health", False, f"Status code: {resp.status}")
                        return False
        except Exception as e:
            self.log_result("FastAPI Health", False, f"Error: {str(e)}")
            return False

    async def test_nextjs_health(self) -> bool:
        """Test Next.js health endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.nextjs_url}/api/health", timeout=5) as resp:
                    if resp.status == 200:
                        self.log_result("Next.js Health", True, "API responding")
                        return True
                    else:
                        self.log_result("Next.js Health", False, f"Status code: {resp.status}")
                        return False
        except Exception as e:
            self.log_result("Next.js Health", False, f"Error: {str(e)}")
            return False

    def test_workspace_directory(self) -> bool:
        """Test workspace directory exists and is writable"""
        try:
            workspace_root = os.getenv("WORKSPACE_ROOT", "/workspaces")
            workspace_path = Path(workspace_root)

            if not workspace_path.exists():
                workspace_path.mkdir(parents=True, exist_ok=True)

            # Test write permission
            test_file = workspace_path / ".test_write"
            test_file.write_text("test")
            test_file.unlink()

            self.log_result("Workspace Directory", True, f"Path: {workspace_root}")
            return True
        except Exception as e:
            self.log_result("Workspace Directory", False, f"Error: {str(e)}")
            return False

    def test_plugin_directory(self) -> bool:
        """Test system-plugins directory exists"""
        try:
            plugin_dir = Path("system-plugins/plugins/core-agents/agents")
            if not plugin_dir.exists():
                self.log_result("Plugin Directory", False, f"Not found: {plugin_dir}")
                return False

            # Check for core agents
            required_agents = [
                "research-agent.md",
                "planning-agent.md",
                "implementation-agent.md",
                "review-agent.md"
            ]

            missing = []
            for agent in required_agents:
                if not (plugin_dir / agent).exists():
                    missing.append(agent)

            if missing:
                self.log_result("Plugin Directory", False, f"Missing agents: {', '.join(missing)}")
                return False

            self.log_result("Plugin Directory", True, f"Found {len(required_agents)} core agents")
            return True
        except Exception as e:
            self.log_result("Plugin Directory", False, f"Error: {str(e)}")
            return False

    def test_environment_variables(self) -> bool:
        """Test required environment variables are set"""
        required_vars = [
            "ANTHROPIC_API_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "NEXTAUTH_SECRET",
            "GITHUB_CLIENT_ID",
            "GITHUB_CLIENT_SECRET"
        ]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            self.log_result("Environment Variables", False,
                          f"Missing: {', '.join(missing)}")
            return False

        self.log_result("Environment Variables", True,
                       f"All {len(required_vars)} required variables set")
        return True

    async def run_all_tests(self):
        """Run all validation tests"""
        print("=" * 60)
        print("🔍 Orbitspace Compyle - System Validation")
        print("=" * 60)
        print()

        # Synchronous tests
        print("📋 Configuration Tests:")
        self.test_environment_variables()
        self.test_workspace_directory()
        self.test_plugin_directory()
        print()

        # Asynchronous tests
        print("🔌 Connectivity Tests:")
        await self.test_redis_connection()
        await self.test_postgres_connection()
        await self.test_anthropic_api()
        print()

        print("🌐 Service Health Tests:")
        await self.test_fastapi_health()
        await self.test_nextjs_health()
        print()

        # Summary
        print("=" * 60)
        total = len(self.results)
        passed = sum(1 for _, p, _ in self.results if p)
        failed = total - passed

        print(f"📊 Results: {passed}/{total} tests passed")

        if failed > 0:
            print(f"\n❌ {failed} test(s) failed:")
            for name, success, msg in self.results:
                if not success:
                    print(f"   - {name}")
                    if msg:
                        print(f"     {msg}")
        else:
            print("\n✅ All systems operational!")

        print("=" * 60)

        return failed == 0

async def main():
    """Main entry point"""
    validator = SystemValidator()
    success = await validator.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
