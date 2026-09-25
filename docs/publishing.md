# Publishing OpenDecision

OpenDecision builds a standard wheel and source distribution with Hatchling. GitHub Actions publishes releases to PyPI through Trusted Publishing.

## First PyPI release

The `opendecision` name was available on PyPI when this packaging setup was created. PyPI package names are normalized, so `OpenDecision`, `opendecision`, and `open-decision` address the same project.

Create a pending Trusted Publisher at [PyPI Publishing](https://pypi.org/manage/account/publishing/) with these values:

| Field | Value |
| --- | --- |
| PyPI project name | `OpenDecision` |
| GitHub owner | `deepanwadhwa` |
| GitHub repository | `OpenDecision` |
| Workflow file | `publish.yml` |
| Environment | `pypi` |

A pending publisher creates the PyPI project when the workflow uploads the first release. It does not reserve the project name before that upload.

Create a GitHub environment named `pypi` under the repository's Settings, Environments page. Add required reviewers or branch restrictions there if desired.

## Build locally

```bash
uv build --python 3.13 --clear
uvx twine check dist/*
```

The build creates:

```text
dist/opendecision-0.1.2-py3-none-any.whl
dist/opendecision-0.1.2.tar.gz
```

## Publish a release

1. Update `version` in `pyproject.toml`.
2. Run `uv lock`.
3. Run the tests and distribution checks.
4. Merge the release commit into the default branch.
5. Create and publish a GitHub release with a tag matching `v<version>`. Version `0.1.2` uses tag `v0.1.2`.

Publishing the GitHub release starts [`.github/workflows/publish.yml`](https://github.com/deepanwadhwa/OpenDecision/blob/main/.github/workflows/publish.yml). The workflow verifies the tag, builds both distributions, checks their metadata, and uploads them to PyPI.

The publish job receives a short-lived credential through GitHub OIDC. The repository does not need a stored PyPI password or API token.

## Verify the public package

Create a clean environment after the workflow completes:

```bash
uv venv --python 3.13 /tmp/opendecision-release-check
uv pip install \
  --python /tmp/opendecision-release-check/bin/python \
  OpenDecision
/tmp/opendecision-release-check/bin/opendecision --version
```
