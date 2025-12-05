import sys
from pathlib import Path

# tests/ から見て 1 つ上 = プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# プロジェクトルートを sys.path の先頭に追加
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

