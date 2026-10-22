"""Suite-wide default: tests never write the person's real decision log (~/.aidlc/logs).
A test that needs a specific log directory sets AIDLC_LOG_DIR itself (e.g. GuardEnv)."""
import atexit
import os
import shutil
import tempfile

if "AIDLC_LOG_DIR" not in os.environ:
    _logs = tempfile.mkdtemp(prefix="aidlc-test-logs-")
    os.environ["AIDLC_LOG_DIR"] = _logs
    atexit.register(shutil.rmtree, _logs, True)
