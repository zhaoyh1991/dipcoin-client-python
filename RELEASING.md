# Releasing Dipcoin Python Client

This document is for package maintainers. Publishing is handled by
`.github/workflows/publish_to_pypi.yml` when a GitHub Release is published.

## First-time PyPI setup

Create a pending Trusted Publisher for the new PyPI project with these values:

- PyPI project: `dipcoin-client`
- Owner: `zhaoyh1991`
- Repository: `dipcoin-client-python`
- Workflow: `publish_to_pypi.yml`
- Environment: `pypi`

No PyPI API token or GitHub repository secret is required.

## Prepare a release

1. Update the version in `pyproject.toml`.
2. Update the release notes in `README.md`.
3. Create a clean Python 3.11 environment and verify the package locally:

   ```bash
   python3.11 -m venv .release-venv
   source .release-venv/bin/activate
   python -m pip install --upgrade pip setuptools wheel build twine
   python -m pip install --editable .
   python -m unittest discover -s tests -v
   python -m build
   python -m twine check dist/*
   ```

4. Commit the release changes and merge them into `main`.

For version `1.3.0`, create and push the tag from the release commit:

```bash
git switch main
git pull --ff-only
git tag -a v1.3.0 -m "Release v1.3.0"
git push origin v1.3.0
```

## Publish the GitHub Release

1. Open the repository's **Releases** page on GitHub.
2. Select **Draft a new release**.
3. Choose the `v1.3.0` tag.
4. Set the release title to `v1.3.0` and add the release notes.
5. Select **Publish release**.

Publishing the release triggers the PyPI workflow. It runs the tests, builds
and checks the source distribution and wheel, then publishes `dipcoin-client`
to PyPI through Trusted Publishing.

Do not reuse a version that has already been uploaded to PyPI. If publishing
fails after an artifact was uploaded, increment the version and create a new
tag and GitHub Release.
