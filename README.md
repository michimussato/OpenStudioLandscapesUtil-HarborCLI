<!-- TOC -->
* [OpenStudioLandscapesUtil-HarborCLI](#openstudiolandscapesutil-harborcli)
  * [Requirements](#requirements)
    * [venv](#venv)
  * [Installation](#installation)
  * [Usage](#usage)
    * [Prepare](#prepare)
    * [Systemd](#systemd)
      * [Install](#install)
      * [Uninstall](#uninstall)
        * [Stop/Disable](#stopdisable)
      * [Status](#status)
      * [Journalctl](#journalctl)
  * [Tagging](#tagging)
    * [Release Candidate](#release-candidate)
    * [Main Release](#main-release)
<!-- TOC -->

---

# OpenStudioLandscapesUtil-HarborCLI

The `openstudiolandscapesutil-harborcli` facilitates getting Harbor up and running for
[OpenStudioLandscapes](https://github.com/michimussato/OpenStudioLandscapes).

`openstudiolandscapesutil-harborcli` is not really intended to be used manually.
It's supposed to be embedded and used by `OpenStudioLandscapes` and it therefore
is therefor feature poor. 

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
usage: OpenStudioLandscapes Harbor CLI [-h] [--version] [-v] [-vv]
                                       {prepare,systemd} ...

A tool to facilitate Harbor setup and getting it up and running using systemd.

positional arguments:
  {prepare,systemd}

options:
  -h, --help           show this help message and exit
  --version            show program's version number and exit
  -v, --verbose        set loglevel to INFO (default: None)
  -vv, --very-verbose  set loglevel to DEBUG (default: None)
```

### Prepare

`cwd` matters.

```shell
cd ~/git/repos/OpenStudioLandscapes/.harbor
```

```shell
openstudiolandscapesutil-harborcli prepare download
```

```shell
openstudiolandscapesutil-harborcli prepare extract --tar-file ./download/harbor-*.tgz
```

```shell
openstudiolandscapesutil-harborcli prepare configure
```

```shell
openstudiolandscapesutil-harborcli prepare install
```

### Systemd

`cwd` matters.

```shell
cd ~/git/repos/OpenStudioLandscapes/.harbor
```

#### Install

```shell
openstudiolandscapesutil-harborcli systemd install --enable --start
```

To directly execute the returned command:

```shell
eval $(openstudiolandscapesutil-harborcli systemd install --enable --start)
```

#### Uninstall

```shell
openstudiolandscapesutil-harborcli systemd uninstall
```

To directly execute the returned command:

```shell
eval $(openstudiolandscapesutil-harborcli systemd uninstall)
```

##### Stop/Disable

To just `stop` and/or `disable`, use the normal `systemctl` commands
- `systemctl stop harbor.service`
- `systemctl disable harbor.service`

#### Status

```shell
openstudiolandscapesutil-harborcli systemd status
```

To directly execute the returned command:

```shell
eval $(openstudiolandscapesutil-harborcli systemd status)
```

#### Journalctl

```shell
openstudiolandscapesutil-harborcli systemd journalctl
```

To directly execute the returned command:

```shell
eval $(openstudiolandscapesutil-harborcli systemd journalctl)
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
