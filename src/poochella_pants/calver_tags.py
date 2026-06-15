"""Mint immutable Docker image tags from the consuming repo's git commit.

Every `docker_image` target in any repo that loads this plugin gets two extra
tags appended to its `image_tags` field:

    <calver>          e.g. 2026.06.14.211722   (committer timestamp, UTC)
    <calver>-<sha>    e.g. 2026.06.14.211722-a49c1d1f0b2c

This replaces the per-repo VERSION/GIT_SHA env wrappers (jj locally, git in
Tekton): the tag is derived inside `pants package`/`publish` from git itself, so
it is identical in every environment. Reads git directly, which also works in a
jj-colocated repo (jj keeps a .git backend).
"""

from __future__ import annotations

from datetime import datetime, timezone

from pants.backend.docker.target_types import DockerImageTags, DockerImageTagsRequest
from pants.engine.rules import collect_rules, implicitly, rule
from pants.engine.unions import UnionRule
from pants.vcs.git import GitWorktreeRequest, get_git_worktree


class CalverImageTagsRequest(DockerImageTagsRequest):
    pass


@rule
async def calver_image_tags(request: CalverImageTagsRequest) -> DockerImageTags:
    maybe_worktree = await get_git_worktree(GitWorktreeRequest(), **implicitly())
    worktree = maybe_worktree.git_worktree
    if worktree is None:
        # No git repo (e.g. an exported tarball build): fall back to whatever
        # static tags the target already declares.
        return DockerImageTags()

    git = worktree._git_binary  # no public API for arbitrary git invocation
    # %cI is the committer date in strict ISO-8601 with the commit's own offset;
    # normalizing to UTC makes the CalVer independent of the build host's TZ and
    # matches doghouse's `jj ... committer.timestamp().utc()`.
    committed_iso = git._invoke_unsandboxed(
        worktree._create_git_cmdline(["show", "-s", "--format=%cI", "HEAD"])
    ).decode().strip()
    calver = datetime.fromisoformat(committed_iso).astimezone(timezone.utc).strftime(
        "%Y.%m.%d.%H%M%S"
    )
    sha = git._invoke_unsandboxed(
        worktree._create_git_cmdline(["rev-parse", "--short=12", "HEAD"])
    ).decode().strip()

    return DockerImageTags([calver, f"{calver}-{sha}"])


def rules():
    return [
        *collect_rules(),
        UnionRule(DockerImageTagsRequest, CalverImageTagsRequest),
    ]
