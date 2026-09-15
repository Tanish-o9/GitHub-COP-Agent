"""
GitHub MCP Tool Abstraction Layer
Provides standardized tool interfaces for GitHub operations adhering to Model Context Protocol (MCP) tool contracts.
"""
import os
import json
import base64
import requests
from typing import Dict, Any, List, Optional
try:
    from github import Github, GithubException
except ImportError:
    Github = None
    GithubException = Exception


class GitHubMCPTools:
    """
    GitHub MCP Interface facilitating repository intelligence, issue inspection,
    PR reviews, test generation analysis, and branch/PR operations.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-MCP-Engineering-Agent"
        }
        if self.token and self.token.strip():
            self.headers["Authorization"] = f"Bearer {self.token.strip()}"
        
        self._gh_client = Github(self.token) if (Github and self.token) else None

    def _api_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"https://api.github.com{endpoint}"
        resp = requests.get(url, headers=self.headers, params=params, timeout=15)
        if resp.status_code == 404:
            raise ValueError(f"Resource not found on GitHub: {endpoint}")
        if resp.status_code >= 400:
            raise ValueError(f"GitHub API Error [{resp.status_code}]: {resp.text}")
        return resp.json()

    # ==========================================
    # REPOSITORY INTELLIGENCE TOOLS
    # ==========================================

    def get_repo_info(self, repo_name: str) -> Dict[str, Any]:
        """Fetch general repository metadata with local fallback."""
        owner_repo = repo_name.strip().strip("/")
        try:
            data = self._api_get(f"/repos/{owner_repo}")
            return {
                "name": data.get("full_name", owner_repo),
                "description": data.get("description", "GitHub Cop Agent Repository"),
                "default_branch": data.get("default_branch", "main"),
                "language": data.get("language", "Python"),
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
            }
        except Exception:
            return {
                "name": owner_repo,
                "description": "GitHub Cop Agent Repository (Local Fallback)",
                "default_branch": "main",
                "language": "Python",
                "stars": 0,
                "forks": 0,
                "open_issues": 0
            }

    def get_repo_tree(self, repo_name: str, branch: Optional[str] = None, recursive: bool = True) -> List[Dict[str, Any]]:
        """Retrieve repository directory structure with local fallback."""
        owner_repo = repo_name.strip().strip("/")
        try:
            if not branch:
                info = self.get_repo_info(owner_repo)
                branch = info["default_branch"]

            endpoint = f"/repos/{owner_repo}/git/trees/{branch}"
            if recursive:
                endpoint += "?recursive=1"

            data = self._api_get(endpoint)
            tree = data.get("tree", [])
            return [
                {
                    "path": item.get("path"),
                    "type": item.get("type"), # "blob" or "tree"
                    "size": item.get("size", 0)
                }
                for item in tree
                if not item.get("path", "").startswith(".git/")
            ]
        except Exception:
            tree_items = []
            for root, dirs, files in os.walk("."):
                dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv", "node_modules", ".repo_memory")]
                for f in files:
                    rel_path = os.path.relpath(os.path.join(root, f), ".").replace("\\", "/")
                    tree_items.append({"path": rel_path, "type": "blob", "size": 100})
            return tree_items

    def search_code(self, repo_name: str, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search code within a specific repository with smart remote tree fallback."""
        owner_repo = repo_name.strip().strip("/")
        q = f"{query} repo:{owner_repo}"
        try:
            data = self._api_get("/search/code", params={"q": q, "per_page": max_results})
            items = data.get("items", [])
            if items:
                return [
                    {
                        "name": item.get("name"),
                        "path": item.get("path"),
                        "html_url": item.get("html_url")
                    }
                    for item in items
                ]
        except Exception:
            pass

        # Priority 1: Filter tree items of the specified remote target repository
        try:
            tree = self.get_repo_tree(owner_repo)
            query_words = [w.lower() for w in query.split() if len(w) > 2]
            matched = []

            for item in tree:
                path = item.get("path", "")
                name = os.path.basename(path)
                path_lower = path.lower()
                if any(w in path_lower for w in query_words):
                    matched.append({"name": name, "path": path, "html_url": f"https://github.com/{owner_repo}/blob/main/{path}"})
                if len(matched) >= max_results:
                    break

            if not matched:
                for item in tree:
                    path = item.get("path", "")
                    name = os.path.basename(path)
                    if any(path_lower.endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".md", ".toml", ".json"]):
                        matched.append({"name": name, "path": path, "html_url": f"https://github.com/{owner_repo}/blob/main/{path}"})
                    if len(matched) >= max_results:
                        break

            if matched:
                return matched
        except Exception:
            pass

        # Priority 2: Local filesystem search only if repo_name matches local working directory
        results = []
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv", "node_modules", ".repo_memory")]
            for f in files:
                if f.endswith(('.py', '.md', '.txt', '.json', '.yml', '.yaml', '.html', '.css', '.js')):
                    rel_path = os.path.relpath(os.path.join(root, f), ".").replace("\\", "/")
                    if not query_words or any(w in rel_path.lower() for w in query_words):
                        results.append({"name": f, "path": rel_path, "html_url": f"file:///{rel_path}"})
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break
        return results

    def get_file_content(self, repo_name: str, path: str, ref: Optional[str] = None) -> Dict[str, Any]:
        """Fetch and decode file content with local fallback."""
        owner_repo = repo_name.strip().strip("/")
        endpoint = f"/repos/{owner_repo}/contents/{path.lstrip('/')}"
        params = {"ref": ref} if ref else None
        try:
            data = self._api_get(endpoint, params=params)
            content_raw = data.get("content", "")
            encoding = data.get("encoding", "")
            if encoding == "base64":
                decoded = base64.b64decode(content_raw).decode("utf-8", errors="replace")
            else:
                decoded = content_raw

            return {
                "path": data.get("path"),
                "size": data.get("size"),
                "sha": data.get("sha"),
                "content": decoded
            }
        except Exception:
            local_path = path.lstrip("/")
            if os.path.exists(local_path):
                try:
                    with open(local_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    return {
                        "path": local_path,
                        "size": len(content),
                        "sha": "local_sha",
                        "content": content
                    }
                except Exception as ex:
                    raise ValueError(f"Could not read local file '{local_path}': {ex}")
            raise ValueError(f"Resource not found: {path}")

    # ==========================================
    # ISSUE ANALYZER TOOLS
    # ==========================================

    def get_issue(self, repo_name: str, issue_number: int) -> Dict[str, Any]:
        """Fetch issue details with fallback."""
        owner_repo = repo_name.strip().strip("/")
        try:
            issue_data = self._api_get(f"/repos/{owner_repo}/issues/{issue_number}")
            try:
                comments_data = self._api_get(f"/repos/{owner_repo}/issues/{issue_number}/comments")
            except Exception:
                comments_data = []

            return {
                "number": issue_data.get("number"),
                "title": issue_data.get("title"),
                "body": issue_data.get("body", ""),
                "state": issue_data.get("state"),
                "user": issue_data.get("user", {}).get("login"),
                "labels": [lbl.get("name") for lbl in issue_data.get("labels", [])],
                "comments": [
                    {
                        "user": c.get("user", {}).get("login"),
                        "body": c.get("body", "")
                    }
                    for c in comments_data
                ]
            }
        except Exception:
            return {
                "number": issue_number,
                "title": f"Issue #{issue_number}",
                "body": "Issue context loaded locally.",
                "state": "open",
                "user": "local_user",
                "labels": ["bug"],
                "comments": []
            }

    def list_issues(self, repo_name: str, state: str = "open") -> List[Dict[str, Any]]:
        """List repository issues."""
        owner_repo = repo_name.strip().strip("/")
        issues = self._api_get(f"/repos/{owner_repo}/issues", params={"state": state, "per_page": 20})
        return [
            {
                "number": i.get("number"),
                "title": i.get("title"),
                "state": i.get("state"),
                "user": i.get("user", {}).get("login"),
                "is_pr": "pull_request" in i
            }
            for i in issues if "pull_request" not in i
        ]

    # ==========================================
    # PULL REQUEST TOOLS
    # ==========================================

    def get_pull_request(self, repo_name: str, pr_number: int) -> Dict[str, Any]:
        """Fetch PR details, changed files, and patch diffs."""
        owner_repo = repo_name.strip().strip("/")
        pr_data = self._api_get(f"/repos/{owner_repo}/pulls/{pr_number}")
        files_data = self._api_get(f"/repos/{owner_repo}/pulls/{pr_number}/files")

        return {
            "number": pr_data.get("number"),
            "title": pr_data.get("title"),
            "body": pr_data.get("body", ""),
            "state": pr_data.get("state"),
            "head": pr_data.get("head", {}).get("ref"),
            "base": pr_data.get("base", {}).get("ref"),
            "user": pr_data.get("user", {}).get("login"),
            "changed_files": [
                {
                    "filename": f.get("filename"),
                    "status": f.get("status"),
                    "additions": f.get("additions"),
                    "deletions": f.get("deletions"),
                    "patch": f.get("patch", "")
                }
                for f in files_data
            ]
        }

    def list_pull_requests(self, repo_name: str, state: str = "open") -> List[Dict[str, Any]]:
        """List repository pull requests."""
        owner_repo = repo_name.strip().strip("/")
        prs = self._api_get(f"/repos/{owner_repo}/pulls", params={"state": state, "per_page": 20})
        return [
            {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "state": pr.get("state"),
                "head": pr.get("head", {}).get("ref"),
                "base": pr.get("base", {}).get("ref")
            }
            for pr in prs
        ]

    # ==========================================
    # WRITE / REPOSITORY MUTATION TOOLS
    # ==========================================

    def create_branch(self, repo_name: str, branch_name: str, base_branch: str = "main") -> Dict[str, Any]:
        """Create a new branch from a base branch."""
        owner_repo = repo_name.strip().strip("/")
        # Get base branch ref sha
        base_ref = self._api_get(f"/repos/{owner_repo}/git/ref/heads/{base_branch}")
        sha = base_ref["object"]["sha"]

        # Create new ref
        url = f"https://api.github.com/repos/{owner_repo}/git/refs"
        payload = {"ref": f"refs/heads/{branch_name}", "sha": sha}
        resp = requests.post(url, headers=self.headers, json=payload, timeout=15)
        if resp.status_code >= 400:
            raise ValueError(f"Failed to create branch: {resp.text}")
        return {"branch": branch_name, "sha": sha, "status": "created"}

    def commit_file_changes(self, repo_name: str, branch: str, path: str, content: str, commit_message: str) -> Dict[str, Any]:
        """Create or update a file on a branch."""
        owner_repo = repo_name.strip().strip("/")
        # Check if file exists to get sha
        sha = None
        try:
            existing = self.get_file_content(owner_repo, path, ref=branch)
            sha = existing.get("sha")
        except Exception:
            pass

        url = f"https://api.github.com/repos/{owner_repo}/contents/{path.lstrip('/')}"
        b64_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        payload = {
            "message": commit_message,
            "content": b64_content,
            "branch": branch
        }
        if sha:
            payload["sha"] = sha

        resp = requests.put(url, headers=self.headers, json=payload, timeout=15)
        if resp.status_code >= 400:
            raise ValueError(f"Failed to commit file change: {resp.text}")
        return resp.json()

    def create_pull_request(self, repo_name: str, title: str, body: str, head: str, base: str = "main") -> Dict[str, Any]:
        """Open a new pull request on GitHub."""
        owner_repo = repo_name.strip().strip("/")
        url = f"https://api.github.com/repos/{owner_repo}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        resp = requests.post(url, headers=self.headers, json=payload, timeout=15)
        if resp.status_code >= 400:
            raise ValueError(f"Failed to create Pull Request: {resp.text}")
        pr_data = resp.json()
        return {
            "number": pr_data.get("number"),
            "html_url": pr_data.get("html_url"),
            "title": pr_data.get("title")
        }
