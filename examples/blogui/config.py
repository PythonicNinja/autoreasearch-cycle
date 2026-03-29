from __future__ import annotations

from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = EXPERIMENT_DIR.parents[1]
PROJECTS_DIR = PROJECT_DIR.parent
BLOG_DIR = PROJECTS_DIR / "pythonic-ninja-blog" / "web"
BLOG_REPO_DIR = BLOG_DIR.parent
DATA_DIR = Path("/tmp/blog-ui-research")
BLOG_GLOBAL_CSS_PATH = BLOG_DIR / "public/styles/global.css"
BLOG_COMPONENTS_DIR = BLOG_DIR / "src/components"
BLOG_BUILD_DIR = "web"
BLOG_GLOBAL_CSS_GIT_PATH = "web/public/styles/global.css"
BLOG_COMPONENTS_GIT_PATH = "web/src/components/"

DOMAIN_ID = "blog_ui"
OPTIMIZER_AGENT = "claude"  # Supported values: "claude", "codex"
EXPERIMENT_NAME = f"blog-ui-{OPTIMIZER_AGENT}-code"
EVAL_THRESHOLD = 0.75
MAX_ITERATIONS = 5

BLOG_EDIT_PATHS = ("web/public/styles/", BLOG_COMPONENTS_GIT_PATH)
LIGHTHOUSE_URL = "http://localhost:4321"
LIGHTHOUSE_CATEGORIES = "accessibility,performance"
DEV_SERVER_WAIT_SECONDS = 10
DEV_SERVER_REQUEST_TIMEOUT_SECONDS = 2
LIGHTHOUSE_TIMEOUT_SECONDS = 180
OPTIMIZER_TIMEOUT_SECONDS = 300
CODEX_BYPASS_APPROVALS_AND_SANDBOX = True
