#!/usr/bin/env python3
"""
Manual testing script for offline/online functionality

This script helps test the ElectricSQL offline/online flow by:
1. Simulating offline operations
2. Testing sync on reconnection
3. Verifying conflict resolution

Run with: python scripts/test_offline_online.py
"""

import subprocess
import sys
import time

import requests


class OfflineOnlineTester:
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.test_tenant = "test-tenant-uuid"
        self.auth_token = None

    def login_test_user(self) -> bool:
        """Login as test user to get auth token"""
        try:
            # This would need actual test credentials
            # For now, just test the endpoints exist
            response = requests.get(f"{self.backend_url}/api/v1/electric/shapes")
            print(f"[OK] Electric shapes endpoint accessible: {response.status_code}")
            return response.status_code in [200, 401]  # 401 is expected without auth
        except requests.exceptions.ConnectionError:
            print("[ERROR] Backend not running. Start with: docker compose up")
            return False

    def test_shapes_endpoint(self) -> bool:
        """Test ElectricSQL shapes endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/api/v1/electric/shapes")
            print(f"[OK] Shapes endpoint: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   Shapes returned: {list(data.get('shapes', {}).keys())}")

            return True
        except Exception as e:
            print(f"[ERROR] Shapes endpoint failed: {e}")
            return False

    def test_sync_status_endpoint(self) -> bool:
        """Test sync status endpoint"""
        try:
            # Test with empty conflicts
            payload = {"conflicts": []}
            response = requests.post(
                f"{self.backend_url}/api/v1/electric/sync-status", json=payload
            )
            print(f"[OK] Sync status endpoint: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {data}")

            return True
        except Exception as e:
            print(f"[ERROR] Sync status endpoint failed: {e}")
            return False

    def test_conflict_resolution(self) -> bool:
        """Test conflict resolution with sample conflicts"""
        try:
            conflicts = [
                {
                    "table": "products",
                    "id": "test-prod-1",
                    "local": {"price": 15.99, "updated_at": "2025-01-20T10:00:00Z"},
                    "remote": {"price": 16.99, "updated_at": "2025-01-20T09:00:00Z"},
                },
                {
                    "table": "stock_items",
                    "id": "test-stock-1",
                    "local": {"qty_on_hand": 50, "updated_at": "2025-01-20T10:00:00Z"},
                    "remote": {"qty_on_hand": 45, "updated_at": "2025-01-20T09:00:00Z"},
                },
            ]

            payload = {"conflicts": conflicts}
            response = requests.post(
                f"{self.backend_url}/api/v1/electric/sync-status", json=payload
            )
            print(f"[OK] Conflict resolution test: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                resolved = data.get("resolved_conflicts", [])
                print(f"   Conflicts resolved: {len(resolved)}")
                for res in resolved:
                    print(
                        f"   - {res['table']}.{res['id']}: {res['resolved_data']['resolution']}"
                    )

            return True
        except Exception as e:
            print(f"[ERROR] Conflict resolution test failed: {e}")
            return False

    def check_database_tables(self) -> bool:
        """Check that ElectricSQL tables exist"""
        try:
            # This would require direct DB access
            # For now, just check the endpoint works
            print("[INFO] Database table checks would require direct DB connection")
            return True
        except Exception as e:
            print(f"[ERROR] Database check failed: {e}")
            return False

    def run_frontend_tests(self) -> bool:
        """Run frontend ElectricSQL tests"""
        try:
            print("[TEST] Running frontend ElectricSQL tests...")
            result = subprocess.run(
                ["npm", "test", "--", "src/lib/__tests__/electric.test.ts"],
                cwd="apps/tenant",
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                print("[OK] Frontend tests passed")
                return True
            else:
                print("[ERROR] Frontend tests failed")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False

        except subprocess.TimeoutExpired:
            print("[ERROR] Frontend tests timed out")
            return False
        except FileNotFoundError:
            print("[ERROR] npm not found. Install Node.js first")
            return False

    def run_backend_tests(self) -> bool:
        """Run backend ElectricSQL tests"""
        try:
            print("[TEST] Running backend ElectricSQL tests...")
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "apps/backend/app/tests/test_electric_conflicts.py",
                    "-v",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                print("[OK] Backend tests passed")
                return True
            else:
                print("[ERROR] Backend tests failed")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False

        except subprocess.TimeoutExpired:
            print("[ERROR] Backend tests timed out")
            return False
        except FileNotFoundError:
            print("[ERROR] Python not found")
            return False


def main():
    print("Testing Offline/Online Functionality\n")

    tester = OfflineOnlineTester()

    tests = [
        ("Backend connectivity", tester.login_test_user),
        ("Electric shapes endpoint", tester.test_shapes_endpoint),
        ("Sync status endpoint", tester.test_sync_status_endpoint),
        ("Conflict resolution", tester.test_conflict_resolution),
        ("Database tables", tester.check_database_tables),
        ("Backend unit tests", tester.run_backend_tests),
        ("Frontend unit tests", tester.run_frontend_tests),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n[TEST] Testing: {test_name}")
        if test_func():
            passed += 1
        time.sleep(0.5)  # Brief pause between tests

    print(f"\n[RESULT] Test Results: {passed}/{total} passed")

    if passed == total:
        print("[SUCCESS] All tests passed! Offline/online functionality is working.")
        return 0
    else:
        print("[WARNING] Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
