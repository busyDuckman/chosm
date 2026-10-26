import os
import tempfile

# disposable db for testing
os.environ.setdefault("CHOSM_DB_URL", f"sqlite:///{tempfile.mkdtemp()}/test_users.db")
