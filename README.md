[![ Logo OpenStudioLandscapes ](https://github.com/michimussato/OpenStudioLandscapes/raw/main/media/images/logo128.png)](https://github.com/michimussato/OpenStudioLandscapes)

---

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
    * [Project](#project)
      * [Create](#create)
      * [Delete](#delete)
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
is feature poor. 

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
usage: OpenStudioLandscapes Harbor CLI [-h] [--version] [-v] [-vv] [--dot-env OPENSTUDIOLANDSCAPES__DOT_ENV] [--user OPENSTUDIOLANDSCAPES__HARBOR_ADMIN] [--password OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD] [--host OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME] [--port OPENSTUDIOLANDSCAPES__HARBOR_PORT]
                                       [--harbor-root-dir OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR]
                                       {prepare,systemd,project} ...

A tool to facilitate Harbor setup and getting it up and running using systemd.

positional arguments:
  {prepare,systemd,project}

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v, --verbose         set loglevel to INFO (default: None)
  -vv, --very-verbose   set loglevel to DEBUG (default: None)
  --dot-env OPENSTUDIOLANDSCAPES__DOT_ENV
                        Full path to the .env file. (default: .env)
  --user OPENSTUDIOLANDSCAPES__HARBOR_ADMIN
                        Harbor Admin User. (default: admin)
  --password OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD
                        Harbor Admin Password. (default: Harbor12345)
  --host OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME
                        The host where Harbor is running (FQDN). (default: harbor.openstudiolandscapes.lan)
  --port OPENSTUDIOLANDSCAPES__HARBOR_PORT
                        The port where Harbor is listening. (default: 80)
  --harbor-root-dir OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR
                        Full path of the Harbor root directory. (default: .harbor)
```

### Environment

```shell
export OPENSTUDIOLANDSCAPES__DOMAIN_LAN=
export OPENSTUDIOLANDSCAPES__DOT_ENV=
export OPENSTUDIOLANDSCAPES__HARBOR_ADMIN=
export OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD=
export OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME=
export OPENSTUDIOLANDSCAPES__HARBOR_PORT=
export OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR=
```

### Prepare

`cwd` matters.

```shell
cd ~/git/repos/OpenStudioLandscapes/.harbor
```

```shell
openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    prepare download \
    --url <https://github.com/goharbor/harbor/releases/download/v2.12.2/harbor-online-installer-v2.12.2.tgz> \
    --destination-directory <download>
```

```shell
openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    prepare extract \
    --extract-to <bin> \
    --tar-file ./download/harbor-*.tgz
```

```shell
openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    prepare configure \
    --destination-directory <bin>
```
(`configure` has a `--dry-run` flag)

```shell
openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    prepare install \
    --prepare-script <bin/prepare>
```

### Systemd

`cwd` matters.

```shell
cd ~/git/repos/OpenStudioLandscapes/.harbor
```

#### Install

```shell
openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    systemd install \
    --enable \
    --start
```

To directly execute the returned command:

```shell
eval $(openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    systemd install \
    --enable \
    --start)
```

#### Uninstall

```shell
openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    systemd uninstall
```

To directly execute the returned command:

```shell
eval $(openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    systemd uninstall)
```

##### Stop/Disable

To just `stop` and/or `disable`, use the normal `systemctl` commands
- `systemctl stop harbor.service`
- `systemctl disable harbor.service`

To follow the journal:
- `journalctl --follow --unit harbor.service`

### Project

`cwd` matters.

```shell
cd ~/git/repos/OpenStudioLandscapes/.harbor
```

#### Create

```shell
openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    project create --project-name openstudiolandscapes
```

To directly execute the returned command:

```shell
eval $(openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    project create --project-name openstudiolandscapes)
```

#### Delete

```shell
openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    project delete --project-name library
```

To directly execute the returned command:

```shell
eval $(openstudiolandscapesutil-harborcli \
    --dot-env ./.env \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    project delete --project-name library)
```

## Tagging

### Release Candidate

```shell
export OPENSTUDIOLANDSCAPES_VERSION_TAG=X.X.X-rcX
```

```shell
git tag --annotate "v${OPENSTUDIOLANDSCAPES_VERSION_TAG}" --message "Release Candidate Version v${OPENSTUDIOLANDSCAPES_VERSION_TAG}" --force
git push --tags --force
```

### Main Release

```shell
export OPENSTUDIOLANDSCAPES_VERSION_TAG=X.X.X
```

```shell
git tag --annotate "v${OPENSTUDIOLANDSCAPES_VERSION_TAG}" --message "Main Release Version v${OPENSTUDIOLANDSCAPES_VERSION_TAG}" --force
git tag --annotate "latest" --message "Latest Release Version (pointing to v${OPENSTUDIOLANDSCAPES_VERSION_TAG})" v${OPENSTUDIOLANDSCAPES_VERSION_TAG}^{} --force
git push --tags --force
```
