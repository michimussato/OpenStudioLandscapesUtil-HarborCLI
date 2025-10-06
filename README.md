<!-- TOC -->
* [OpenStudioLandscapesUtil-HarborCLI](#openstudiolandscapesutil-harborcli)
  * [Requirements](#requirements)
    * [venv](#venv)
  * [Installation](#installation)
  * [Usage](#usage)
  * [Tagging](#tagging)
    * [Release Candidate](#release-candidate)
    * [Main Release](#main-release)
<!-- TOC -->

---

# OpenStudioLandscapesUtil-HarborCLI

The `openstudiolandscapesutil-harborcli` facilitates getting Harbor up and running for
[OpenStudioLandscapes](https://github.com/michimussato/OpenStudioLandscapes).

This package was created using PyScaffold:

```shell
putup --package Harbor_CLI --venv .venv --no-tox --license AGPL-3.0-or-later --force --namespace OpenStudioLandscapesUtil OpenStudioLandscapesUtil-HarborCLI
```

## Requirements

- `python3.11`

### venv

```shell
python3 -m venv .venv
source .venv/bin/activate
```

## Installation

`pip install git+https://github.com/michimussato/OpenStudioLandscapesUtil-HarborCLI.git`

## Usage

```
$ openstudiolandscapesutil-harborcli --help
Usage: openstudiolandscapesutil-harborcli [OPTIONS] COMMAND [ARGS]...

  A Harbor CLI entrypoint.

Options:
  -v, --verbosity TEXT  Set verbosity of output: CRITICAL, FATAL, ERROR, WARN,
                        WARNING, INFO, DEBUG, NOTSET
  --help                Show this message and exit.

Commands:
  configure          Step 3
  download           Step 1
  extract            Step 2
  prepare            Step 4
  systemd-install    Step 5
  systemd-uninstall
```

## Tagging

### Release Candidate

```shell
NEW_TAG=X.X.X-rcX
```

```shell
git tag --annotate "v${NEW_TAG}" --message "Release Candidate Version v${NEW_TAG}" --force
git push --tags --force
```

### Main Release

```shell
NEW_TAG=X.X.X
```

```shell
git tag --annotate "v${NEW_TAG}" --message "Main Release Version v${NEW_TAG}" --force
git tag --annotate "latest" --message "Latest Release Version (pointing to v${NEW_TAG})" v${NEW_TAG}^{} --force
git push --tags --force
```
