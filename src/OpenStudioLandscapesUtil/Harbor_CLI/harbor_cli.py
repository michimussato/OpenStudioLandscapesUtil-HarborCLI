"""
This is a skeleton file that can serve as a starting point for a Python
console script. To run this script uncomment the following lines in the
``[options.entry_points]`` section in ``setup.cfg``::

    console_scripts =
         fibonacci = Harbor_CLI.skeleton:run

Then run ``pip install .`` (or ``pip install -e .`` for editable mode)
which will install the command ``fibonacci`` inside your current environment.

Besides console scripts, the header (i.e. until ``_logger``...) of this file can
also be used as template for Python modules.

Note:
    This file can be renamed depending on your needs or safely removed if not needed.

References:
    - https://setuptools.pypa.io/en/latest/userguide/entry_point.html
    - https://pip.pypa.io/en/stable/reference/pip_install
"""
import argparse
import base64
import configparser
import enum
from dotenv import load_dotenv
import os
import pathlib
import shutil
import subprocess
import tarfile
import typing
from subprocess import CompletedProcess
from typing import Union, Any, Dict

import requests
import logging
import sys

import yaml
from OpenStudioLandscapesUtil.Harbor_CLI import __version__


dotenv: pathlib.Path = pathlib.Path(__file__).parent.parent.parent.parent.joinpath(".env")

load_dotenv(
    dotenv_path=dotenv,
    verbose=True,
)


__author__ = "Michael Mussato"
__copyright__ = "Michael Mussato"
__license__ = "AGPL-3.0-or-later"

_logger = logging.getLogger(__name__)


# DEFAULTS

SHELL = [
    shutil.which("bash"),
    "-c",
]
_SU_METHODS= {
    "su": [
        shutil.which("su"),
        "-",
        "root",
    ],
    "sudo": [
        shutil.which("sudo"),
        "--user=root",
    ],
    "pkexec": [
        shutil.which("pkexec"),
    ],
}

SU_METHOD = _SU_METHODS["pkexec"]

HARBOR_URL: str = "https://github.com/goharbor/harbor/releases/download/v2.12.2/harbor-online-installer-v2.12.2.tgz"
HARBOR_ROOT_DIR: pathlib.Path = pathlib.Path(os.environ.get("HARBOR_ROOT_DIR", "~/git/repos/OpenStudioLandscapes/.harbor")).expanduser().resolve()
_HARBOR_DOWNLOAD_DIR: str = "download"
HARBOR_DOWNLOAD_DIR: pathlib.Path = HARBOR_ROOT_DIR.joinpath(_HARBOR_DOWNLOAD_DIR)
_HARBOR_BIN_DIR: str = "bin"
HARBOR_BIN_DIR: pathlib.Path = HARBOR_ROOT_DIR.joinpath(_HARBOR_BIN_DIR)
_HARBOR_DATA_DIR: str = "data"
HARBOR_DATA_DIR: pathlib.Path = HARBOR_ROOT_DIR.joinpath(_HARBOR_DATA_DIR)
HARBOR_CONFIG_ROOT: pathlib.Path = HARBOR_BIN_DIR
_HARBOR_PREPARE: str = "prepare"
HARBOR_PREPARE: pathlib.Path = HARBOR_BIN_DIR.joinpath(_HARBOR_PREPARE)

OPENSTUDIOLANDSCAPES__DOMAIN_LAN: str = os.environ.get("OPENSTUDIOLANDSCAPES__DOMAIN_LAN" ,"farm.evil")
OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME: str = "harbor.{OPENSTUDIOLANDSCAPES__DOMAIN_LAN}".format(OPENSTUDIOLANDSCAPES__DOMAIN_LAN=OPENSTUDIOLANDSCAPES__DOMAIN_LAN)
OPENSTUDIOLANDSCAPES__HARBOR_PORT: int = int(os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_PORT", 80))
OPENSTUDIOLANDSCAPES__HARBOR_ADMIN: str = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_ADMIN", "admin")
OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD: str = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD", "Harbor12345")

OPENSTUDIOLANDSCAPES__HARBOR_API_ENDPOINT: str = "http://{host}:{port}/api/v2.0"

HARBOR_CONFIG_DICT: dict = {
    "hostname": OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME,
    "http": {"port": OPENSTUDIOLANDSCAPES__HARBOR_PORT},
    "harbor_admin_password": OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD,
    "database": {
        "password": "root123",
        "max_idle_conns": 100,
        "max_open_conns": 900,
        "conn_max_idle_time": 0,
    },
    "data_volume": HARBOR_DATA_DIR.as_posix(),
    "trivy": {
        "ignore_unfixed": False,
        "skip_update": False,
        "skip_java_db_update": False,
        "offline_scan": False,
        "security_check": "vuln",
        "insecure": False,
        "timeout": "5m0s",
    },
    "jobservice": {
        "max_job_workers": 10,
        "job_loggers": ["STD_OUTPUT", "FILE"],
        "logger_sweeper_duration": 1,
    },
    "notification": {
        "webhook_job_max_retry": 3,
        "webhook_job_http_client_timeout": 3,
    },
    "log": {
        "level": "info",
        "local": {
            "rotate_count": 50,
            "rotate_size": "200M",
            "location": "/var/log/harbor",
        },
    },
    "_version": "2.12.0",
    "proxy": {
        "http_proxy": None,
        "https_proxy": None,
        "no_proxy": None,
        "components": ["core", "jobservice", "trivy"],
    },
    "upload_purging": {
        "enabled": True,
        "age": "168h",
        "interval": "24h",
        "dryrun": False,
    },
    "cache": {"enabled": False, "expire_hours": 24},
}

SYSTEMD_UNIT: pathlib.Path = pathlib.Path("/usr/lib/systemd/system/harbor.service")

DOCKER_PROGRESS = [
    "auto",
    "quiet",
    "plain",
    "tty",
    "rawjson",
]


class RequestMethod(enum.StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"


class HarborCLIError(Exception):
    pass


# ---- Python API ----
# The functions defined in this section can be imported by users in their
# Python scripts/interactive interpreter, e.g. via
# `from OpenStudioLandscapesUtil.Harbor_CLI.harbor_cli import fib`,
# when using this Python module as a library.


def auth_tokenized() -> str:
    return f"{base64.b64encode(str(':'.join([OPENSTUDIOLANDSCAPES__HARBOR_ADMIN, OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD])).encode('utf-8')).decode('ascii')}"


def curlify(
        request: requests.PreparedRequest,
) -> list[str]:
    cmd = [
        shutil.which("curl"),
        "-X",
        request.method,
    ]

    headers = ['-H "{0}: {1}"'.format(k, v) for k, v in request.headers.items()]
    cmd.extend(
        [
            *headers,
        ]
    )

    if request.body is not None:
        data = request.body.decode("utf-8")
        cmd.extend(
            [
                "-d",
                f"'{data}'",
            ]
        )

    uri = request.url
    cmd.append(f"'{uri}'")

    return cmd


def download(
        url: str,
        destination_directory: pathlib.Path,
) -> Union[pathlib.Path, Exception]:
    """Step 1"""

    destination_directory = destination_directory.expanduser().resolve()

    _logger.debug(url)
    _logger.debug(destination_directory)

    destination_directory.mkdir(parents=True, exist_ok=True)

    if not destination_directory.exists():
        destination_directory.mkdir(
            parents=True, exist_ok=True
        )  # create folder if it does not exist

    tar_filename = url.split("/")[-1].replace(" ", "_")  # be careful with file names
    tar_file_path = destination_directory / tar_filename

    r = requests.get(url, stream=True)
    if r.ok:
        _logger.info("Saving to %s" % tar_file_path.absolute().as_posix())
        with open(tar_file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 8):
                if chunk:
                    f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())

        return tar_file_path

    else:  # HTTP status code 4XX/5XX
        raise Exception(
            "Download failed: status code {}\n{}".format(r.status_code, r.text)
        )


def extract(
        extract_to: pathlib.Path,
        tar_file: pathlib.Path,
) -> Union[pathlib.Path, Exception]:
    """Step 2"""

    extract_to = extract_to.expanduser().resolve()
    tar_file = tar_file.expanduser().resolve()

    if extract_to == tar_file.parent:
        raise HarborCLIError(
            f"{tar_file.as_posix()} should be extracted to a subdirectory."
        ) from FileNotFoundError(tar_file)


    if extract_to.exists():
        if bool(list(extract_to.iterdir())):
            raise HarborCLIError(
                f"{extract_to.as_posix()} is not empty. "
                f"Aborted. Clear it first if that's "
                f"really what you want."
            )

    if not tar_file.exists():
        raise HarborCLIError(
            f"{tar_file.as_posix()} not found."
        ) from FileNotFoundError(tar_file)


    _logger.debug(extract_to)
    _logger.debug(tar_file)

    harbor_bin_dir: pathlib.Path = extract_to
    harbor_bin_dir.mkdir(parents=True, exist_ok=True)

    # equivalent to tar --strip-components=1
    # Credits: https://stackoverflow.com/a/78461535
    strip1 = lambda member, path: member.replace(
        name=pathlib.Path(*pathlib.Path(member.path).parts[1:])
    )

    _logger.debug("Extracting tar file...")
    with tarfile.open(tar_file, "r:gz") as tar:
        tar.extractall(
            path=harbor_bin_dir,
            filter=strip1,
        )
    _logger.debug("All files extracted to %s" % harbor_bin_dir.as_posix())

    return extract_to


def _configure() -> str:

    harbor_yml: str = yaml.dump(
        HARBOR_CONFIG_DICT,
        indent=2,
    )

    return harbor_yml


def configure(
        out_dir: pathlib.Path,
        overwrite: bool = False,
) -> Union[pathlib.Path, Exception]:
    """Step 3"""

    out_dir: pathlib.Path = out_dir.expanduser().resolve()

    _logger.debug(out_dir)

    harbor_yml: pathlib.Path = out_dir.joinpath("harbor.yml")
    harbor_yml.parent.mkdir(parents=True, exist_ok=True)

    if not overwrite:
        if harbor_yml.exists():
            raise HarborCLIError(
                f"{harbor_yml.as_posix()} already exists."
            ) from FileExistsError(harbor_yml)

    harbor_yml_data: str = _configure()

    with open(harbor_yml, "w") as fw:
        fw.write(harbor_yml_data)

    return harbor_yml


def prepare(
        prepare_script: pathlib.Path,
        config_file: pathlib.Path = None,
) -> CompletedProcess[bytes]:
    """Step 4"""

    prepare_script = prepare_script.expanduser().resolve()

    if config_file is not None:
        config_file = config_file.expanduser().resolve()

        # if not HARBOR_CONFIG_ROOT.joinpath("harbor.yml").exists():
        if not config_file.exists():
            raise HarborCLIError(
                f"`harbor.yml` file not found at {config_file.as_posix()}. "
                f"Run `openstudiolandscapesutil-harborcli configure`."
            )

    _logger.debug(prepare_script)

    if not prepare_script.exists():
        raise FileNotFoundError("`prepare` file not found. Not able to continue.")

    if prepare_script.parent.joinpath("common").exists():
        raise HarborCLIError(
            "Harbor prepare has already been run. Remove "
            "`common` directory first before rerunning."
        ) from FileExistsError(prepare_script.parent.joinpath("common"))

    _logger.debug("Preparing Harbor...")

    bash_c = [
        # *su_method,
        *SHELL,
    ]

    cmd_prepare = [
        prepare_script.as_posix(),
    ]

    if config_file is not None:
        cmd_prepare.extend(
            [
                "--conf",
                config_file.as_posix()
            ]
        )

    _logger.debug(f"{' '.join(bash_c)} \"{' '.join(cmd_prepare)}\"")

    cmd = [
        *bash_c,
        ' '.join(cmd_prepare),
    ]

    _logger.debug(cmd)

    proc = subprocess.Popen(
        [
            *bash_c,
            ' '.join(cmd_prepare),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        shell=False,
    )

    for line in proc.stdout:
        sys.stdout.write(line)

    proc.wait()

    return proc.returncode


def _systemd_unit_dict(
        working_directory: pathlib.Path,
        exec_start: typing.List[str],
        exec_reload: typing.List[str],
        exec_stop: typing.List[str],
) -> typing.Dict:

    unit_dict = {
        "Unit": {
            "Description": "Harbor",
            "Documentation": "https://goharbor.io/",
        },
        "Service": {
            "Type": "simple",
            "User": "root",
            "Group": "root",
            "Restart": "always",
            "WorkingDirectory": working_directory.as_posix(),
            "ExecStart": " ".join(exec_start),
            "ExecReload": " ".join(exec_reload),
            "ExecStop": " ".join(exec_stop),
        },
        "Install": {
            "WantedBy": "multi-user.target",
        },
    }

    _logger.debug(unit_dict)

    return unit_dict


def systemd_install(
        su_method: str,
        enable: bool,
        start: bool,
        # install: bool,
        outfile: pathlib.Path = HARBOR_BIN_DIR.joinpath(SYSTEMD_UNIT.name),  # this is just the temp file
) -> list[str | Any]:
    """Step 5"""

    outfile = outfile.expanduser().resolve()

    _logger.debug(start)
    _logger.debug(enable)

    _cmd_harbor = [
        shutil.which("docker"),
        "compose",
        "--progress",
        DOCKER_PROGRESS[2],
        "--file",
        HARBOR_CONFIG_ROOT.joinpath("docker-compose.yml").as_posix(),
        "--project-name",
        "openstudiolandscapes-harbor",
    ]

    exec_start = [
        *_cmd_harbor,
        "up",
        "--remove-orphans",
    ]

    exec_reload = [
        *_cmd_harbor,
        "restart",
    ]

    exec_stop = [
        *_cmd_harbor,
        "down",
    ]

    unit_dict: dict = _systemd_unit_dict(
        working_directory=HARBOR_BIN_DIR,
        exec_start=exec_start,
        exec_reload=exec_reload,
        exec_stop=exec_stop,
    )

    unit: configparser.ConfigParser = configparser.ConfigParser()
    # Change from case insensitive to case sensitive
    # https://docs.python.org/3/library/configparser.html#configparser.ConfigParser.optionxform
    unit.optionxform = str

    unit.read_dict(unit_dict)

    unit_file_tmp = outfile

    unit_file_tmp.parent.mkdir(parents=True, exist_ok=True)

    with open(unit_file_tmp, "w") as fw:
        unit.write(fw, space_around_delimiters=False)

    with open(unit_file_tmp, "r") as fr:
        unit_file_content = fr.read()

    _logger.debug(unit_file_content)

    copy_service = [
        shutil.which("cp"),
        unit_file_tmp.as_posix(),
        SYSTEMD_UNIT.as_posix(),
    ]

    set_permissions = [
        shutil.which("chmod"),
        "644",
        SYSTEMD_UNIT.as_posix(),
    ]

    daemon_reload = [
        shutil.which("systemctl"),
        "daemon-reload",
    ]

    systemctl_start = [
        shutil.which("systemctl"),
        "start",
        SYSTEMD_UNIT.name,
    ]

    systemctl_enable = [
        shutil.which("systemctl"),
        "enable",
        SYSTEMD_UNIT.name,
    ]

    install_service = [
        *copy_service,
        "&&",
        *set_permissions,
        "&&",
        *daemon_reload,
    ]

    if start:
        install_service.extend(
            [
                "&&",
                *systemctl_start,
            ]
        )

    if enable:
        install_service.extend(
            [
                "&&",
                *systemctl_enable,
            ]
        )

    _logger.debug(f"{install_service = }")

    sudo_bash_c = [
        *_SU_METHODS[su_method],
        *SHELL,
    ]

    cmd = [
        *sudo_bash_c,
        " ".join(install_service)
    ]

    # _logger.debug(f"{cmd = }")

    # proc = subprocess.run(
    #     [
    #         *sudo_bash_c,
    #         " ".join(install_service)
    #     ],
    #     shell=True,
    #     check=True,
    # )

    _logger.info("Execute the following command manually:")
    print(f"{' '.join(sudo_bash_c)} \"{' '.join(install_service)}\"")

    return cmd


def systemd_uninstall(
        su_method: str,
        disable: bool = True,
        stop: bool = True,
        remove: bool = True,
) -> list[str | Any]:

    if remove:
        stop = True
        disable = True

    _logger.debug(stop)
    _logger.debug(disable)
    _logger.debug(remove)

    systemctl_disable = [
        shutil.which("systemctl"),
        "disable",
        "--now",
        SYSTEMD_UNIT.name,
    ]

    remove_service = [
        shutil.which("rm"),
        SYSTEMD_UNIT.as_posix(),
    ]

    daemon_reload = [
        shutil.which("systemctl"),
        "daemon-reload",
    ]

    uninstall_service = [
        *systemctl_disable,
        "&&",
        *remove_service,
        "&&",
        *daemon_reload,
    ]

    _logger.debug(f"{uninstall_service = }")

    sudo_bash_c = [
        *_SU_METHODS[su_method],
        *SHELL,
    ]

    cmd = [
        *sudo_bash_c,
        " ".join(uninstall_service)
    ]

    # _logger.debug(f"{cmd = }")

    # proc = subprocess.run(
    #     [
    #         *sudo_bash_c,
    #         " ".join(install_service)
    #     ],
    #     shell=True,
    #     check=True,
    # )

    _logger.info("Execute the following command manually:")
    print(f"{' '.join(sudo_bash_c)} \"{' '.join(uninstall_service)}\"")

    return cmd


def systemd_status() -> list[str | Any]:

    systemctl_status = [
        shutil.which("systemctl"),
        "--full",
        "--no-pager",
        SYSTEMD_UNIT.name,
    ]

    _logger.debug(f"{systemctl_status = }")

    sudo_bash_c = [
        # *SU_METHOD,
        *SHELL,
    ]

    cmd = [
        *sudo_bash_c,
        " ".join(systemctl_status)
    ]

    # _logger.debug(f"{cmd = }")

    # proc = subprocess.run(
    #     [
    #         *sudo_bash_c,
    #         " ".join(install_service)
    #     ],
    #     shell=True,
    #     check=True,
    # )

    _logger.info("Execute the following command manually:")
    print(f"{' '.join(sudo_bash_c)} \"{' '.join(systemctl_status)}\"")

    return cmd


def systemd_journalctl() -> list[str | Any]:

    journalctl_fu = [
        shutil.which("journalctl"),
        "--follow",
        "--unit",
        SYSTEMD_UNIT.name,
    ]

    _logger.debug(f"{journalctl_fu = }")

    sudo_bash_c = [
        # *SU_METHOD,
        *SHELL,
    ]

    cmd = [
        *sudo_bash_c,
        " ".join(journalctl_fu)
    ]

    # proc = subprocess.run(
    #     [
    #         *sudo_bash_c,
    #         " ".join(install_service)
    #     ],
    #     shell=True,
    #     check=True,
    # )

    _logger.info("Execute the following command manually:")
    print(f"{' '.join(sudo_bash_c)} \"{' '.join(journalctl_fu)}\"")

    return cmd


def project_create(
        project_name: str,
        host: str,
        port: int,
) -> list[str | Any]:

    def project_create_request_dict(project_name_) -> Dict:
        _project_create_dict: dict = {
            "endpoint": f"{OPENSTUDIOLANDSCAPES__HARBOR_API_ENDPOINT.format(host=host, port=port)}/projects",
            "method": RequestMethod.POST.value,
            "headers": {
                "accept": "application/json",
                "authorization": f"Basic {auth_tokenized()}",
                "X-Resource-Name-In-Location": "false",
                "Content-Type": "application/json",
            },
            "payload": {
                # json encoding happens automatically.
                # no need to wrap this dict in json.dumps()
                # https://stackoverflow.com/questions/25242262/dump-to-json-adds-additional-double-quotes-and-escaping-of-quotes
                "json": {
                    "project_name": project_name_,
                    "public": True,
                },
            }
        }
        return _project_create_dict

    def project_create_request_prepared(
            request_dict: Dict,
    ) -> requests.PreparedRequest:

        payload = request_dict["payload"]

        _logger.debug(f"{payload = }")

        request: requests.Request = requests.Request(
            method=request_dict["method"],
            url=request_dict["endpoint"],
            headers=request_dict["headers"],
            **payload,
        )

        return request.prepare()

    prepared_request = project_create_request_prepared(
        request_dict=project_create_request_dict(
            project_name_=project_name
        ),
    )

    # sudo_bash_c = [
    #     # *_SU_METHODS[su_method],
    #     *SHELL,
    # ]

    cmd: list = curlify(prepared_request)

    _logger.info("Execute the following command manually:")
    print(f"{' '.join(cmd)}")

    return cmd


def project_delete(
        project_name: str,
        host: str,
        port: int,
) -> list[str | Any]:

    def project_delete_request_dict(project_name_) -> Dict:
        _project_delete_dict: dict = {
            "endpoint": f"{OPENSTUDIOLANDSCAPES__HARBOR_API_ENDPOINT.format(host=host, port=port)}/projects/{project_name_}",
            "method": RequestMethod.DELETE.value,
            "headers": {
                "accept": "application/json",
                "X-Is-Resource-Name": "false",
                "authorization": f"Basic {auth_tokenized()}",
            },
            "payload": {
                # # json encoding happens automatically.
                # # no need to wrap this dict in json.dumps()
                # # https://stackoverflow.com/questions/25242262/dump-to-json-adds-additional-double-quotes-and-escaping-of-quotes
                # "json": {
                #     "project_name": project_name_,
                #     "public": True,
                # },
            }
        }
        return _project_delete_dict

    def project_delete_request_prepared(
            request_dict: Dict,
    ) -> requests.PreparedRequest:

        # payload = request_dict["payload"]
        #
        # _logger.debug(f"{payload = }")

        request: requests.Request = requests.Request(
            method=request_dict["method"],
            url=request_dict["endpoint"],
            headers=request_dict["headers"],
            # **payload,
        )

        return request.prepare()

    prepared_request = project_delete_request_prepared(
        request_dict=project_delete_request_dict(
            project_name_=project_name
        ),
    )

    # sudo_bash_c = [
    #     # *_SU_METHODS[su_method],
    #     *SHELL,
    # ]

    cmd: list = curlify(prepared_request)

    _logger.info("Execute the following command manually:")
    print(f"{' '.join(cmd)}")

    return cmd


# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.


def eval_(
        args: argparse.Namespace,
) -> Union[pathlib.Path, subprocess.CompletedProcess, list, None]:

    _logger.debug(f"{args = }")

    _logger.debug(f"{args.command = }")

    if args.command == "prepare":
        _logger.debug(f"{args.prepare_command = }")

        if args.prepare_command == "download":
            result: pathlib.Path = _cli_download(args)
            _logger.debug(f"{result = }")
            return result

        elif args.prepare_command == "extract":
            result: pathlib.Path = _cli_extract(args)
            _logger.debug(f"{result = }")
            return result

        elif args.prepare_command == "configure":
            if args.dry_run:
                # from pprint import pprint
                print(_configure())
                return None
            else:
                result = _cli_configure(args)
                _logger.debug(f"{result = }")
                return result

        elif args.prepare_command == "install":
            result: subprocess.CompletedProcess = _cli_install(args)
            _logger.debug(f"{result = }")
            return result

    elif args.command == "systemd":
        _logger.debug(f"{args.systemd_command = }")

        if args.systemd_command == "install":
            result: list = _cli_systemd_install(args)
            _logger.debug(f"{result = }")
            return result

        elif args.systemd_command == "uninstall":
            result: list = _cli_systemd_uninstall(args)
            _logger.debug(f"{result = }")
            return result

        elif args.systemd_command == "status":
            result: list = _cli_systemd_status()
            _logger.debug(f"{result = }")
            return result

        elif args.systemd_command == "journalctl":
            result: list = _cli_systemd_journalctl()
            _logger.debug(f"{result = }")
            return result

    elif args.command == "project":
        _logger.debug(f"{args.project_command = }")

        if args.project_command == "create":
            result: list = _cli_project_create(args)
            _logger.debug(f"{result = }")
            return result

        if args.project_command == "delete":
            result: list = _cli_project_delete(args)
            _logger.debug(f"{result = }")
            return result


def _cli_download(
        args: argparse.Namespace,
) -> pathlib.Path:

    result = download(
        url=args.url,
        destination_directory=args.destination_directory,
    )

    return result


def _cli_extract(
        args: argparse.Namespace,
) -> pathlib.Path:

    result = extract(
        extract_to=args.extract_to,
        tar_file=args.tar_file,
    )

    return result


def _cli_configure(
        args: argparse.Namespace,
) -> pathlib.Path:

    result: pathlib.Path = configure(
        out_dir=args.destination_directory,
        overwrite=args.overwrite,
    )

    return result


def _cli_install(
        args: argparse.Namespace,
) -> subprocess.CompletedProcess:

    result: subprocess.CompletedProcess = prepare(
        prepare_script=args.prepare_script,
        config_file=None,  # args.config_file,
    )

    return result


def _cli_systemd_install(
        args: argparse.Namespace,
) -> list:

    result: list = systemd_install(
        su_method=args.su_method,
        enable=args.enable,
        start=args.start,
        outfile=args.outfile,
    )

    return result


def _cli_systemd_uninstall(
        args: argparse.Namespace,
) -> list:

    result: list = systemd_uninstall(
        su_method=args.su_method,
    )

    return result


def _cli_systemd_status() -> list:

    result: list = systemd_status()

    return result


def _cli_systemd_journalctl() -> list:

    result: list = systemd_journalctl()

    return result


def _cli_project_create(
        args: argparse.Namespace,
) -> list:

    result: list = project_create(
        project_name=args.project_name,
        host=args.host,
        port=args.port,
    )

    return result


def _cli_project_delete(
        args: argparse.Namespace,
) -> list:

    result: list = project_delete(
        project_name=args.project_name,
        host=args.host,
        port=args.port,
    )

    return result


_formatter = argparse.ArgumentDefaultsHelpFormatter


def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    main_parser = argparse.ArgumentParser(
        prog="OpenStudioLandscapes Harbor CLI",
        description="A tool to facilitate Harbor setup and "
                    "getting it up and running using systemd.",
        formatter_class=_formatter,
    )
    main_parser.add_argument(
        "--version",
        action="version",
        version=f"OpenStudioLandscapesUtil-ReadmeGenerator {__version__}",
    )
    # parser.add_argument(dest="n", help="n-th Fibonacci number", type=int, metavar="INT")
    main_parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        # action="count",
        # https://stackoverflow.com/questions/6076690/verbose-level-with-argparse-and-multiple-v-options
        const=logging.INFO,
    )
    main_parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )

    base_subparsers = main_parser.add_subparsers(
        dest="command",
    )

    ####################################################################################################################
    # PREPARE

    base_subparser_prepare = base_subparsers.add_parser(
        name="prepare",
        formatter_class=_formatter,
    )

    prepare_subparsers = base_subparser_prepare.add_subparsers(
        dest="prepare_command",
    )

    ## DOWNLOAD

    subparser_download = prepare_subparsers.add_parser(
        name="download",
        formatter_class=_formatter,
        help="Download the Harbor Release from GitHub. "
             "Existing files will be overwritten.",
    )

    subparser_download.add_argument(
        "--url",
        "-u",
        dest="url",
        required=False,
        default=HARBOR_URL,
        help="URL of the Harbor Installer TAR.",
        metavar="URL",
        type=str,
    )

    subparser_download.add_argument(
        "--destination-directory",
        "-d",
        dest="destination_directory",
        required=False,
        default=pathlib.Path().cwd().joinpath(_HARBOR_DOWNLOAD_DIR),
        help="Where to save the downloaded files.",
        metavar="DESTINATION_DIRECTORY",
        type=pathlib.Path,
    )

    ## EXTRACT

    subparser_extract = prepare_subparsers.add_parser(
        name="extract",
        formatter_class=_formatter,
    )

    subparser_extract.add_argument(
        "--extract-to",
        "-x",
        dest="extract_to",
        required=False,
        default=pathlib.Path().cwd().joinpath(_HARBOR_BIN_DIR),
        help="Full path where the files will be extracted to "
             "(no subdirectories will be created).",
        metavar="EXTRACT_TO",
        type=pathlib.Path,
    )

    subparser_extract.add_argument(
        "--tar-file",
        "-f",
        dest="tar_file",
        required=True,
        # Todo
        #  - [ ] default=pathlib.Path().cwd().joinpath(_HARBOR_DOWNLOAD_DIR, "harbor-*.tgz"),
        help="Full path to the downloaded Harbor Release tar.",
        metavar="TAR_FILE",
        type=pathlib.Path,
    )

    # Todo
    #  - [ ] --clear
    # mutex_extract.add_argument(
    #     "--clear",
    #     "-c",
    #     dest="clear",
    #     action="store_true",
    #     required=False,
    #     default=False,
    #     help="Remove the extracted files.",
    #     # metavar="CLEAR",
    #     # type=bool,
    # )

    ## CONFIGURE

    subparser_configure = prepare_subparsers.add_parser(
        name="configure",
        formatter_class=_formatter,
    )

    mutex_configure = subparser_configure.add_mutually_exclusive_group()

    mutex_configure.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        required=False,
        default=False,
        help="Print the configuration to stdout.",
    )

    mutex_configure.add_argument(
        "--destination-directory",
        "-d",
        dest="destination_directory",
        required=False,
        default=pathlib.Path().cwd().joinpath(_HARBOR_BIN_DIR),
        help="Directory where to save the harbor.yml file.",
        metavar="DESTINATION_DIRECTORY",
        type=pathlib.Path,
    )

    subparser_configure.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        required=False,
        default=False,
        help="Force overwriting existing harbor.yml file.",
    )

    ## PREPARE

    subparser_run_prepare = prepare_subparsers.add_parser(
        name="install",
        formatter_class=_formatter,
    )

    subparser_run_prepare.add_argument(
        "--prepare-script",
        "-s",
        dest="prepare_script",
        required=False,
        default=pathlib.Path().cwd().joinpath(_HARBOR_BIN_DIR, "prepare"),
        help="Full path to the extracted prepare script.",
        metavar="PREPARE_SCRIPT",
        type=pathlib.Path,
    )

    # This is not working as expected:
    # $ ./prepare --help
    # prepare base dir is set to /home/michael/git/repos/OpenStudioLandscapesUtil-HarborCLI/test/extracted
    # Usage: main.py prepare [OPTIONS]
    #
    # Options:
    #   --conf TEXT   the path of Harbor configuration file
    #   --with-trivy  the Harbor instance is to be deployed with Trivy
    #   --help        Show this message and exit.
    # Clean up the input dir
    #
    # subparser_run_prepare.add_argument(
    #     "--config-file",
    #     "-c",
    #     dest="config_file",
    #     required=False,
    #     default=pathlib.Path().cwd().joinpath("harbor.yml"),
    #     help="Full path to the harbor.yml config file.",
    #     metavar="CONFIG_FILE",
    #     type=pathlib.Path,
    # )

    ####################################################################################################################
    # SYSTEMD

    base_subparser_systemd = base_subparsers.add_parser(
        name="systemd",
        formatter_class=_formatter,
    )

    systemd_subparsers = base_subparser_systemd.add_subparsers(
        dest="systemd_command",
        help="A command generator for setting up "
             "systemd with Harbor."
    )

    ## INSTALL

    subparser_install = systemd_subparsers.add_parser(
        name="install",
        formatter_class=_formatter,
        help="Install systemd unit.",
    )

    subparser_install.add_argument(
        "--su-method",
        dest="su_method",
        required=False,
        choices=_SU_METHODS.keys(),
        default="pkexec",
        help=f"Which SU method to use: {list(_SU_METHODS.keys())}.",
        metavar="SU_METHOD",
        type=str,
    )

    subparser_install.add_argument(
        "--outfile",
        "-f",
        dest="outfile",
        required=False,
        default=pathlib.Path().cwd().joinpath(_HARBOR_BIN_DIR, SYSTEMD_UNIT.name),
        help="Where to save the intermediate unit file. "
             "It will get copied to the final destination "
             "upon command completion.",
        metavar="OUTFILE",
        type=pathlib.Path,
    )

    subparser_install.add_argument(
        "--enable",
        dest="enable",
        action="store_true",
        required=False,
        default=False,
        help="Enable systemd unit.",
    )

    subparser_install.add_argument(
        "--start",
        # "-d",
        dest="start",
        action="store_true",
        required=False,
        default=False,
        help="Start systemd unit.",
    )

    ## UNINSTALL

    subparser_uninstall = systemd_subparsers.add_parser(
        name="uninstall",
        formatter_class=_formatter,
        help="Stop, disable and uninstall systemd unit.",
    )

    subparser_uninstall.add_argument(
        "--su-method",
        dest="su_method",
        required=False,
        choices=_SU_METHODS.keys(),
        default="pkexec",
        help=f"Which SU method to use: {list(_SU_METHODS.keys())}.",
        metavar="SU_METHOD",
        type=str,
    )

    ## STATUS

    subparser_status = systemd_subparsers.add_parser(
        name="status",
        formatter_class=_formatter,
        help="Systemd unit status.",
    )

    ## JOURNALCTL

    subparser_journalctl = systemd_subparsers.add_parser(
        name="journalctl",
        formatter_class=_formatter,
        help="Follow logs.",
    )

    ####################################################################################################################
    # PROJECT

    base_subparser_systemd = base_subparsers.add_parser(
        name="project",
        formatter_class=_formatter,
    )

    project_subparsers = base_subparser_systemd.add_subparsers(
        dest="project_command",
        help="A simple interface to set up the basic "
             "project structure in Harbor."
    )

    ## CREATE

    subparser_project_create = project_subparsers.add_parser(
        name="create",
        formatter_class=_formatter,
        help="Create project.",
    )

    subparser_project_create.add_argument(
        "--project-name",
        "-p",
        dest="project_name",
        required=True,
        default="openstudiolandscapes",
        help="The name of the project to be created.",
        metavar="PROJECT_NAME",
        type=str,
    )

    subparser_project_create.add_argument(
        "--host",
        # "-h",
        dest="host",
        required=False,
        default=OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME,
        help="The host where Harbor is running.",
        metavar="HOST",
        type=str,
    )

    subparser_project_create.add_argument(
        "--port",
        # "-p",
        dest="port",
        required=False,
        default=OPENSTUDIOLANDSCAPES__HARBOR_PORT,
        help="The port where Harbor is listening.",
        metavar="PORT",
        type=int,
    )

    ## DELETE

    subparser_project_delete = project_subparsers.add_parser(
        name="delete",
        formatter_class=_formatter,
        help="Delete project.",
    )

    subparser_project_delete.add_argument(
        "--project-name",
        "-p",
        dest="project_name",
        required=True,
        default="library",
        help="The name of the project to be deleted.",
        metavar="PROJECT_NAME",
        type=str,
    )

    subparser_project_delete.add_argument(
        "--host",
        # "-h",
        dest="host",
        required=False,
        default=OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME,
        help="The host where Harbor is running.",
        metavar="HOST",
        type=str,
    )

    subparser_project_delete.add_argument(
        "--port",
        # "-p",
        dest="port",
        required=False,
        default=OPENSTUDIOLANDSCAPES__HARBOR_PORT,
        help="The port where Harbor is listening.",
        metavar="PORT",
        type=int,
    )

    return main_parser.parse_args()


def setup_logging(
        args: argparse.Namespace,
):
    """Setup basic logging

    Args:
      args (argparse.Namespace): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=args.loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )

    _logger.debug("Logging setup complete")
    _logger.debug(f"Logging Level: {logging.getLevelName(_logger.getEffectiveLevel())}")

    _logger.debug("args: %s", args)


def main(args):
    """Wrapper allowing :func:`fib` to be called with string arguments in a CLI fashion

    Instead of returning the value from :func:`fib`, it prints the result to the
    ``stdout`` in a nicely formatted message.

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--verbose", "42"]``).
    """
    args: argparse.Namespace = parse_args(args)
    setup_logging(args)
    eval_(args)


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    # ^  This is a guard statement that will prevent the following code from
    #    being executed in the case someone imports this file instead of
    #    executing it as a script.
    #    https://docs.python.org/3/library/__main__.html

    # After installing your project with pip, users can also run your Python
    # modules as scripts via the ``-m`` flag, as defined in PEP 338::
    #
    #     python -m OpenStudioLandscapesUtil.Harbor_CLI.skeleton 42
    #
    run()
