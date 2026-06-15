# poochella-pants

Shared [pantsbuild](https://www.pantsbuild.org/) plugin for the poochella
homelab. One job today: stamp every `docker_image` with immutable,
VCS-derived tags so the CalVer-from-git logic lives in **one place** instead of
being re-ported into each repo's justfile (jj) and Tekton task (git).

## What it does

Appends two tags to every `docker_image` target's `image_tags`:

| tag              | example                          |
| ---------------- | -------------------------------- |
| `<calver>`       | `2026.06.14.211722`              |
| `<calver>-<sha>` | `2026.06.14.211722-a49c1d1f0b2c` |

`<calver>` is the HEAD committer timestamp normalized to UTC; `<sha>` is the
12-char short commit id. Derived inside `pants package`/`publish`, so it is the
same locally and in CI — no `VERSION`/`GIT_SHA` env vars, no jj-vs-git drift.
Reads git directly (works in jj-colocated repos via the `.git` backend).

## Consuming it

In each repo's `pants.toml`:

```toml
[GLOBAL]
backend_packages = [
    "pants.backend.docker",
    "poochella_pants",
]
# Pin to a tag or commit so plugin resolves are reproducible.
plugins = ["poochella-pants @ git+ssh://git@github.com/Ivanipani/poochella-pants.git@v0.1.0"]
```

Then keep BUILD files minimal — the plugin supplies the version tags:

```python
docker_image(
    name="ci-builder",
    repository="ci-builder",
    registries=["@poochella"],
    image_tags=["latest"],
)
```

Drop any `build_args = ["VERSION", "GIT_SHA"]` and the env-var wrappers; the
revision is recoverable from the `<calver>-<sha>` tag.

## Releasing a new version

Bump `version` in `pyproject.toml`, tag the commit, push the tag, then bump the
pinned `@vX.Y.Z` in each consumer's `pants.toml`.
