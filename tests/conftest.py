import os
import sys
import tempfile
from pathlib import Path

# Configure the app before it is imported: isolated data dir, API mode with a
# dummy key (the pipeline itself is replaced by a fake in tests).
_tmp = tempfile.mkdtemp(prefix="intellilecture_test_")
os.environ.update({
    "DATA_DIR": _tmp,
    "AI_PROVIDER": "api",
    "GROQ_API_KEY": "test-key",
    "UPLOADS_PER_HOUR": "1000",
    "MAX_UPLOAD_MB": "1",
    "FRONTEND_DIST": str(Path(_tmp) / "no-dist"),
})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
