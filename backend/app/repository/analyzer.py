"""Git repository abstraction — wraps GitPython for change-set analysis."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import git
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ChangedFile:
    path: str
    change_type: str  # A=added, M=modified, D=deleted, R=renamed
    additions: int = 0
    deletions: int = 0
    diff_text: str = ""
    content: Optional[str] = None


@dataclass
class ChangeMap:
    base_ref: str
    target_ref: str
    changed_files: List[ChangedFile] = field(default_factory=list)
    commit_messages: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    def files_by_extension(self, ext: str) -> List[ChangedFile]:
        return [f for f in self.changed_files if f.path.endswith(ext)]

    def files_matching(self, patterns: List[str]) -> List[ChangedFile]:
        import fnmatch
        result = []
        for f in self.changed_files:
            if any(fnmatch.fnmatch(f.path, p) for p in patterns):
                result.append(f)
        return result

    def to_dict(self) -> dict:
        return {
            "base_ref": self.base_ref,
            "target_ref": self.target_ref,
            "changed_files": [
                {
                    "path": f.path,
                    "change_type": f.change_type,
                    "additions": f.additions,
                    "deletions": f.deletions,
                }
                for f in self.changed_files
            ],
            "commit_messages": self.commit_messages,
            "stats": self.stats,
        }


class RepositoryAnalyzer:
    """Wraps a local Git repository for diff/content analysis."""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path).resolve()
        try:
            self.repo = git.Repo(str(self.repo_path))
        except git.InvalidGitRepositoryError:
            # Initialize a new repo for the demo-repository
            self.repo = git.Repo.init(str(self.repo_path))
            logger.warning("repo_initialized_as_new", path=str(self.repo_path))

    def build_change_map(self, base_ref: str, target_ref: str) -> ChangeMap:
        """Compute the diff between two refs."""
        change_map = ChangeMap(base_ref=base_ref, target_ref=target_ref)

        try:
            base_commit = self.repo.commit(base_ref)
            target_commit = self.repo.commit(target_ref)
            diff = base_commit.diff(target_commit)

            for item in diff:
                change_type = item.change_type  # A, M, D, R, etc.
                path = item.b_path or item.a_path

                # Read content of changed file from target
                content: Optional[str] = None
                try:
                    if item.b_blob:
                        raw = item.b_blob.data_stream.read()
                        content = raw.decode("utf-8", errors="replace")
                except Exception:
                    pass

                diff_text = ""
                try:
                    diff_text = item.diff.decode("utf-8", errors="replace") if item.diff else ""
                except Exception:
                    pass

                # Count +/- lines
                additions = sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
                deletions = sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---"))

                change_map.changed_files.append(
                    ChangedFile(
                        path=path,
                        change_type=change_type,
                        additions=additions,
                        deletions=deletions,
                        diff_text=diff_text,
                        content=content,
                    )
                )

            # Collect commit messages between refs
            commits = list(self.repo.iter_commits(f"{base_ref}..{target_ref}"))
            change_map.commit_messages = [c.message.strip() for c in commits]

            change_map.stats = {
                "total_files": len(change_map.changed_files),
                "total_additions": sum(f.additions for f in change_map.changed_files),
                "total_deletions": sum(f.deletions for f in change_map.changed_files),
                "commit_count": len(commits),
            }

        except Exception as exc:
            logger.error("change_map_failed", error=str(exc), base=base_ref, target=target_ref)
            # Return empty change map rather than crashing
            change_map.stats = {"error": str(exc)}

        return change_map

    def read_file_at_ref(self, file_path: str, ref: str) -> Optional[str]:
        """Read the content of a file at a specific git ref."""
        try:
            blob = self.repo.commit(ref).tree[file_path]
            return blob.data_stream.read().decode("utf-8", errors="replace")
        except Exception:
            # Fall back to reading from disk
            disk_path = self.repo_path / file_path
            if disk_path.exists():
                return disk_path.read_text(errors="replace")
            return None

    def read_file_from_disk(self, file_path: str) -> Optional[str]:
        """Read the current on-disk content of a file."""
        full = self.repo_path / file_path
        if full.exists():
            return full.read_text(errors="replace")
        return None

    def list_all_files(self, ref: str = "HEAD") -> List[str]:
        """List all tracked files at a ref."""
        try:
            tree = self.repo.commit(ref).tree
            return [blob.path for blob in tree.traverse() if blob.type == "blob"]
        except Exception:
            return []
