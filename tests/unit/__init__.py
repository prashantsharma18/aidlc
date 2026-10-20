"""Unit tests. Doctor's D13 reads user and managed Claude Code settings; point it at paths that do
not exist, so the developer's own files never change a test result."""
import os

os.environ.setdefault("AIDLC_USER_SETTINGS", "/nonexistent/aidlc-unit-tests/user-settings.json")
os.environ.setdefault("AIDLC_MANAGED_SETTINGS", "/nonexistent/aidlc-unit-tests/managed-settings.json")
