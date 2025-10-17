[![ Logo OpenStudioLandscapes ](https://github.com/michimussato/OpenStudioLandscapes/raw/main/media/images/logo128.png)](https://github.com/michimussato/OpenStudioLandscapes)

---

<!-- TOC -->
* [OpenStudioLandscapesUtil-HarborCLI](#openstudiolandscapesutil-harborcli)
  * [Requirements](#requirements)
    * [venv](#venv)
  * [Installation](#installation)
  * [Usage](#usage)
    * [Environment](#environment)
      * [Environment Variables vs. .env](#environment-variables-vs-env)
    * [Prepare](#prepare)
    * [Systemd](#systemd)
      * [Install](#install)
      * [Uninstall](#uninstall)
        * [Stop/Disable](#stopdisable)
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
usage: OpenStudioLandscapes Harbor CLI [-h] [--version] [-v] [-vv] [--user OPENSTUDIOLANDSCAPES__HARBOR_ADMIN] [--password OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD] [--host OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME] [--port OPENSTUDIOLANDSCAPES__HARBOR_PORT]
                                       [--harbor-root-dir OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR] [--harbor-download OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR] [--harbor-bin OPENSTUDIOLANDSCAPES__HARBOR_BIN_DIR] [--harbor-data OPENSTUDIOLANDSCAPES__HARBOR_DATA_DIR]
                                       [--harbor-prepare OPENSTUDIOLANDSCAPES__HARBOR_PREPARE]
                                       {prepare,systemd,project} ...

A tool to facilitate Harbor setup and getting it up and running using systemd.

positional arguments:
  {prepare,systemd,project}

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v, --verbose         set loglevel to INFO (default: None)
  -vv, --very-verbose   set loglevel to DEBUG (default: None)
  --user OPENSTUDIOLANDSCAPES__HARBOR_ADMIN
                        Harbor Admin User. (default: admin)
  --password OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD
                        Harbor Admin Password. (default: Harbor12345)
  --host OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME
                        The host where Harbor is running (FQDN). (default: harbor.{OPENSTUDIOLANDSCAPES__DOMAIN_LAN})
  --port OPENSTUDIOLANDSCAPES__HARBOR_PORT
                        The port where Harbor is listening. (default: 80)
  --harbor-root-dir OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR
                        Full path of the Harbor root directory. (default: /home/michael/git/repos/OpenStudioLandscapes/.harbor)
  --harbor-download OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR
                        Where to save the downloaded files (subdirectory of OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR). (default: download)
  --harbor-bin OPENSTUDIOLANDSCAPES__HARBOR_BIN_DIR
                        Name of the bin directory (subdirectory of OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR). (default: bin)
  --harbor-data OPENSTUDIOLANDSCAPES__HARBOR_DATA_DIR
                        Name of the data directory (subdirectory of OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR). (default: data)
  --harbor-prepare OPENSTUDIOLANDSCAPES__HARBOR_PREPARE
                        Name of the prepare file (file of the OPENSTUDIOLANDSCAPES__HARBOR_BIN subdirectory). (default: prepare)
```

### Environment

Some options (and their default values) for the `openstudiolandscapes-harborcli`
command are based on the existence/values of environment variables. 
If such values are not in the environment, the options are _required_. 
If such values are specified in the environment, these options are _optional_ 
and would **override** the values available in the environment.

```shell
export OPENSTUDIOLANDSCAPES__HARBOR_ADMIN=
export OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD=
export OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME=
export OPENSTUDIOLANDSCAPES__HARBOR_PORT=
export OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR=
```

Assumed, we have the following `.env` file:

```
export OPENSTUDIOLANDSCAPES__HARBOR_ADMIN=admin
export OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD=Harbor12345
export OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME=harbor.openstudiolandscapes.lan
export OPENSTUDIOLANDSCAPES__HARBOR_PORT=80
export OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR=./.harbor
```

> [!NOTE]
> Or use the stowed `.env` from the [stow](https://github.com/michimussato/stow)
> repository (not public):
> 
> ```shell
> REPOS_DIR=~/git/repos
> stow --override .env --dir ${REPOS_DIR}/stow/env/OpenStudioLandscapes --target ${REPOS_DIR}/OpenStudioLandscapesUtil-HarborCLI --stow openstudiolandscapes.cloud-ip.cc -vvv
> ```
> 
> More info: on `stow` [here](https://www.gnu.org/software/stow/).

...these commands are equivalent:

```shell
openstudiolandscapesutil-harborcli \
    --user admin \
    --password Harbor12345 \
    --host harbor.openstudiolandscapes.lan \
    --port 80 \
    --harbor-root-dir ./.harbor \
    prepare download \
    --url https://github.com/goharbor/harbor/releases/download/v2.12.2/harbor-online-installer-v2.12.2.tgz \
    --destination-directory download
```

and

```shell
source .env
openstudiolandscapesutil-harborcli \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    prepare download \
    --url https://github.com/goharbor/harbor/releases/download/v2.12.2/harbor-online-installer-v2.12.2.tgz \
    --destination-directory download
```

and

```shell
source .env
openstudiolandscapesutil-harborcli \
    prepare download
```

However, these are not:

```shell
source .env
openstudiolandscapesutil-harborcli \
    --port 8080 \
    prepare download
```

which would act as a shortcut for:

```shell
source .env
openstudiolandscapesutil-harborcli \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port 8080 \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    prepare download \
    --url https://github.com/goharbor/harbor/releases/download/v2.12.2/harbor-online-installer-v2.12.2.tgz \
    --destination-directory download
```

#### Environment Variables vs. .env

Instead of specifying all variables manually, we can leverage `.env` files
potentially already available:

```shell
source .env
```

### Prepare

`cwd` matters.

```shell
cd ~/git/repos/OpenStudioLandscapes/.harbor
```

```shell
openstudiolandscapesutil-harborcli \
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
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    prepare extract \
    --tar-file ./download/harbor-*.tgz
```

```shell
openstudiolandscapesutil-harborcli \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    prepare configure
```

(`configure` has a `--dry-run` flag)

```shell
openstudiolandscapesutil-harborcli \
    --user ${OPENSTUDIOLANDSCAPES__HARBOR_USERNAME} \
    --password ${OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD} \
    --host ${OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME} \
    --port ${OPENSTUDIOLANDSCAPES__HARBOR_PORT} \
    --harbor-root-dir ${OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR} \
    prepare install
```

### Systemd

`cwd` matters.

```shell
cd ~/git/repos/OpenStudioLandscapes/.harbor
```

#### Install

```shell
openstudiolandscapesutil-harborcli \
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
