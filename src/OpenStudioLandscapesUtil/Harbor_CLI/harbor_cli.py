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

# Todo
#  - [ ] Switch to .env
# Required Environment Variables
# OPENSTUDIOLANDSCAPES__DOT_ENV: pathlib.Path = pathlib.Path(os.environ.get("OPENSTUDIOLANDSCAPES__DOT_ENV", ".env"))
OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR: pathlib.Path = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR", ".harbor")
OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME: str = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME" ,"openstudiolandscapes-harbor.openstudiolandscapes.lan")
OPENSTUDIOLANDSCAPES__HARBOR_PORT: int = int(os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_PORT", "80"))
OPENSTUDIOLANDSCAPES__HARBOR_ADMIN: str = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_ADMIN", "admin")
OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD: str = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD", "Harbor12345")

OPENSTUDIOLANDSCAPES__HARBOR_INSTALLER: str = os.environ.get(
    "OPENSTUDIOLANDSCAPES__HARBOR_INSTALLER",
    "https://github.com/goharbor/harbor/releases/download/v2.12.2/harbor-online-installer-v2.12.2.tgz",
)
OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR: str = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR", "download")
OPENSTUDIOLANDSCAPES__HARBOR_BIN_DIR: str = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_BIN_DIR", "bin")
OPENSTUDIOLANDSCAPES__HARBOR_DATA_DIR: str = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_DATA_DIR", "data")
OPENSTUDIOLANDSCAPES__HARBOR_PREPARE: str = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_PREPARE", "prepare")
OPENSTUDIOLANDSCAPES__HARBOR_API_ENDPOINT: str = os.environ.get("OPENSTUDIOLANDSCAPES__HARBOR_API_ENDPOINT", "/api/v2.0")

# OPENSTUDIOLANDSCAPES__HARBOR_API_ENDPOINT: str = "http://{host}:{port}/api/v2.0"

SYSTEMD_UNIT: pathlib.Path = pathlib.Path("/usr/lib/systemd/system/openstudiolandscapes-harbor.service")

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


def auth_tokenized(
        user: str,
        password: str,
) -> str:
    return f"{base64.b64encode(str(':'.join([user, password])).encode('utf-8')).decode('ascii')}"


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


def _configure(args) -> str:

    harbor_config_dict: dict = {
        "hostname": args.host,
        "http": {"port": args.port},
        "harbor_admin_password": args.password,
        "database": {
            "password": "root123",
            "max_idle_conns": 100,
            "max_open_conns": 900,
            "conn_max_idle_time": 0,
        },
        "data_volume": args.harbor_root_dir.joinpath(args.harbor_data).expanduser().resolve().as_posix(),
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
        "_version": os.environ["OPENSTUDIOLANDSCAPES__HARBOR_RELEASE"],
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

    harbor_yml: str = yaml.dump(
        harbor_config_dict,
        indent=2,
    )

    return harbor_yml


def configure(
        destination_directory: pathlib.Path,
        overwrite: bool,
        harbor_yml_data: str,
) -> Union[pathlib.Path, Exception]:
    """Step 3"""

    destination_directory = destination_directory.expanduser().resolve()

    _logger.debug(destination_directory)

    harbor_yml: pathlib.Path = destination_directory.joinpath("harbor.yml")
    harbor_yml.parent.mkdir(parents=True, exist_ok=True)

    if not overwrite:
        if harbor_yml.exists():
            raise HarborCLIError(
                f"{harbor_yml.as_posix()} already exists."
            ) from FileExistsError(harbor_yml)

    with open(harbor_yml, "w") as fw:
        fw.write(harbor_yml_data)

    return harbor_yml


def prepare(
        prepare_script: pathlib.Path,
        # config_file: pathlib.Path = None,
) -> CompletedProcess[bytes]:
    """Step 4"""

    prepare_script = prepare_script.expanduser().resolve()

    # if config_file is not None:
    #     config_file = config_file.expanduser().resolve()
    #
    #     # if not HARBOR_CONFIG_ROOT.joinpath("harbor.yml").exists():
    #     if not config_file.exists():
    #         raise HarborCLIError(
    #             f"`harbor.yml` file not found at {config_file.as_posix()}. "
    #             f"Run `openstudiolandscapesutil-harborcli configure`."
    #         )

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

    # if config_file is not None:
    #     cmd_prepare.extend(
    #         [
    #             "--conf",
    #             config_file.as_posix()
    #         ]
    #     )

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


def systemd_unit_dict(
        working_directory: pathlib.Path,
        exec_start: typing.List[str],
        exec_reload: typing.List[str],
        exec_stop: typing.List[str],
) -> typing.Dict:

    unit_dict = {
        "Unit": {
            "Description": "Harbor for OpenStudioLandscapes",
            "Documentation": "https://github.com/michimussato/OpenStudioLandscapes/blob/main/wiki/guides/harbor.md",
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
        outfile: pathlib.Path,
        start: bool,
        enable: bool,
        harbor_bin_dir: pathlib.Path,
) -> list[str | Any]:
    """Step 5"""

    outfile = pathlib.Path(outfile).expanduser().resolve()

    _logger.debug(start)
    _logger.debug(enable)

    _cmd_harbor = [
        shutil.which("docker"),
        "compose",
        "--progress",
        DOCKER_PROGRESS[2],
        "--file",
        harbor_bin_dir.joinpath("docker-compose.yml").as_posix(),
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

    unit_dict: dict = systemd_unit_dict(
        working_directory=harbor_bin_dir,
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
        disable: bool,
        stop: bool,
        uninstall: bool,
) -> list[str | Any]:

    if uninstall:
        stop = True
        disable = True

    _logger.debug(stop)
    _logger.debug(disable)
    _logger.debug(uninstall)

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
        host: str,
        port: int,
        user: str,
        password: str,
        project_name: str,
) -> list[str | Any]:

    def project_create_request_dict(project_name_) -> Dict:
        _project_create_dict: dict = {
            "endpoint": f"http://{host}:{port}{OPENSTUDIOLANDSCAPES__HARBOR_API_ENDPOINT}/projects",
            # "endpoint": f"{OPENSTUDIOLANDSCAPES__HARBOR_API_ENDPOINT.format(host=host, port=port)}/projects",
            "method": RequestMethod.POST.value,
            "headers": {
                "accept": "application/json",
                "authorization": f"Basic {auth_tokenized(user=user, password=password)}",
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
        host: str,
        port: int,
        user: str,
        password: str,
        project_name: str,
) -> list[str | Any]:

    def project_delete_request_dict(project_name_) -> Dict:
        _project_delete_dict: dict = {
            "endpoint": f"http://{host}:{port}{OPENSTUDIOLANDSCAPES__HARBOR_API_ENDPOINT}/projects/{project_name_}",
            "method": RequestMethod.DELETE.value,
            "headers": {
                "accept": "application/json",
                "X-Is-Resource-Name": "false",
                "authorization": f"Basic {auth_tokenized(user=user, password=password)}",
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

    # dotenv_ = args.dot_env
    #
    # if dotenv_ is not None:
    #     dotenv_: pathlib.Path = args.dot_env.expanduser().resolve()
    #     if not dotenv_.exists():
    #         raise FileNotFoundError(f"{dotenv_.as_posix()} does not exist")
    #
    # load_dotenv(
    #     dotenv_path=dotenv_,
    #     verbose=True,
    # )

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
                print(_configure(args))
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
        destination_directory=args.harbor_root_dir.joinpath(args.harbor_download),
    )

    return result


def _cli_extract(
        args: argparse.Namespace,
) -> pathlib.Path:

    result = extract(
        extract_to=args.harbor_root_dir.joinpath(args.harbor_bin),
        tar_file=args.tar_file,
    )

    return result


def _cli_configure(
        args: argparse.Namespace,
) -> pathlib.Path:

    harbor_yml_data: str = _configure(args=args)

    result: pathlib.Path = configure(
        destination_directory=args.harbor_root_dir.joinpath(args.harbor_bin),
        overwrite=args.overwrite,
        harbor_yml_data=harbor_yml_data,
    )

    return result


def _cli_install(
        args: argparse.Namespace,
) -> subprocess.CompletedProcess:

    result: subprocess.CompletedProcess = prepare(
        prepare_script=args.harbor_root_dir.joinpath(args.harbor_bin, args.harbor_prepare),
        # config_file=None,  # args.config_file,
    )

    return result


def _cli_systemd_install(
        args: argparse.Namespace,
) -> list:

    result: list = systemd_install(
        su_method=args.su_method,
        outfile=args.outfile,
        start=args.start,
        enable=args.enable,
        harbor_bin_dir=args.harbor_root_dir.joinpath(args.harbor_bin),
    )

    return result


def _cli_systemd_uninstall(
        args: argparse.Namespace,
) -> list:

    result: list = systemd_uninstall(
        su_method=args.su_method,
        disable=args.disable,
        stop=args.stop,
        uninstall=args.uninstall,
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
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        project_name=args.project_name,
    )

    return result


def _cli_project_delete(
        args: argparse.Namespace,
) -> list:

    result: list = project_delete(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        project_name=args.project_name,
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
    # main_parser.add_argument(
    #     # "-e",
    #     "--dot-env",
    #     dest="dot_env",
    #     required=not bool(OPENSTUDIOLANDSCAPES__DOT_ENV),
    #     default=pathlib.Path(OPENSTUDIOLANDSCAPES__DOT_ENV) if bool(OPENSTUDIOLANDSCAPES__DOT_ENV) else None,
    #     help="Full path to the .env file.",
    #     metavar="OPENSTUDIOLANDSCAPES__DOT_ENV",
    #     type=pathlib.Path,
    # )

    main_parser.add_argument(
        "--user",
        # "-h",
        dest="user",
        required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_ADMIN),
        default=OPENSTUDIOLANDSCAPES__HARBOR_ADMIN if bool(OPENSTUDIOLANDSCAPES__HARBOR_ADMIN) else None,
        help="Harbor Admin User.",
        metavar="OPENSTUDIOLANDSCAPES__HARBOR_ADMIN",
        type=str,
    )

    main_parser.add_argument(
        "--password",
        # "-h",
        dest="password",
        required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD),
        default=OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD if bool(OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD) else None,
        help="Harbor Admin Password.",
        metavar="OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD",
        type=str,
    )

    main_parser.add_argument(
        "--host",
        # "-h",
        dest="host",
        required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME),
        default=OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME if bool(OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME) else None,
        help="The host where Harbor is running (FQDN).",
        metavar="OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME",
        type=str,
    )

    main_parser.add_argument(
        "--port",
        # "-p",
        dest="port",
        required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_PORT),
        default=OPENSTUDIOLANDSCAPES__HARBOR_PORT if bool(OPENSTUDIOLANDSCAPES__HARBOR_PORT) else None,
        help="The port where Harbor is listening.",
        metavar="OPENSTUDIOLANDSCAPES__HARBOR_PORT",
        type=int,
    )

    main_parser.add_argument(
        "--harbor-root-dir",
        # "-hrd",
        dest="harbor_root_dir",
        required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR),
        default=OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR if bool(OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR) else None,
        help="Full path of the Harbor root directory.",
        metavar="OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR",
        type=pathlib.Path,
    )

    main_parser.add_argument(
        "--harbor-download",
        # "-hrd",
        dest="harbor_download",
        required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR),
        default=OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR if bool(OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR) else None,
        help="Where to save the downloaded files "
             "(subdirectory of OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR).",
        metavar="OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR",
        type=str,
    )

    main_parser.add_argument(
        "--harbor-bin",
        # "-hrd",
        dest="harbor_bin",
        required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_BIN_DIR),
        default=OPENSTUDIOLANDSCAPES__HARBOR_BIN_DIR if bool(OPENSTUDIOLANDSCAPES__HARBOR_BIN_DIR) else None,
        help="Name of the bin directory "
             "(subdirectory of OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR).",
        metavar="OPENSTUDIOLANDSCAPES__HARBOR_BIN_DIR",
        type=str,
    )

    main_parser.add_argument(
        "--harbor-data",
        # "-hrd",
        dest="harbor_data",
        required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_DATA_DIR),
        default=OPENSTUDIOLANDSCAPES__HARBOR_DATA_DIR if bool(OPENSTUDIOLANDSCAPES__HARBOR_DATA_DIR) else None,
        help="Name of the data directory "
             "(subdirectory of OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR).",
        metavar="OPENSTUDIOLANDSCAPES__HARBOR_DATA_DIR",
        type=str,
    )

    main_parser.add_argument(
        "--harbor-prepare",
        # "-hrd",
        dest="harbor_prepare",
        required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_PREPARE),
        default=OPENSTUDIOLANDSCAPES__HARBOR_PREPARE if bool(OPENSTUDIOLANDSCAPES__HARBOR_PREPARE) else None,
        help="Name of the prepare file "
             "(file of the OPENSTUDIOLANDSCAPES__HARBOR_BIN subdirectory).",
        metavar="OPENSTUDIOLANDSCAPES__HARBOR_PREPARE",
        type=str,
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
        required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_INSTALLER),
        default=OPENSTUDIOLANDSCAPES__HARBOR_INSTALLER if bool(OPENSTUDIOLANDSCAPES__HARBOR_INSTALLER) else None,
        help="URL of the Harbor Installer TAR.",
        metavar="URL",
        type=str,
    )

    # subparser_download.add_argument(
    #     "--destination-directory",
    #     "-d",
    #     dest="destination_directory",
    #     required=not bool(OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR),
    #     default=OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR if bool(OPENSTUDIOLANDSCAPES__HARBOR_DOWNLOAD_DIR) else None,
    #     help="Where to save the downloaded files "
    #          "(subdirectory of OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR).",
    #     metavar="DESTINATION_DIRECTORY",
    #     type=str,
    # )

    ## EXTRACT

    subparser_extract = prepare_subparsers.add_parser(
        name="extract",
        formatter_class=_formatter,
    )

    # subparser_extract.add_argument(
    #     "--extract-to",
    #     "-x",
    #     dest="extract_to",
    #     required=False,
    #     default=pathlib.Path().cwd().joinpath(_HARBOR_BIN_DIR),
    #     help="Where to extract the files to "
    #          "(subdirectory of OPENSTUDIOLANDSCAPES__HARBOR_ROOT_DIR).",
    #     metavar="EXTRACT_TO",
    #     type=str,
    # )

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

    # mutex_configure.add_argument(
    #     "--destination-directory",
    #     "-d",
    #     dest="destination_directory",
    #     required=False,
    #     default=pathlib.Path().cwd().relative_to(pathlib.Path().cwd()).joinpath(_HARBOR_BIN_DIR),
    #     help="Directory where to save the harbor.yml file.",
    #     metavar="DESTINATION_DIRECTORY",
    #     type=str,
    # )

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

    # subparser_run_prepare.add_argument(
    #     "--prepare-script",
    #     "-s",
    #     dest="prepare_script",
    #     required=False,
    #     default=pathlib.Path().cwd().joinpath(_HARBOR_BIN_DIR, _HARBOR_PREPARE),
    #     help="Full path to the extracted prepare script.",
    #     metavar="PREPARE_SCRIPT",
    #     type=pathlib.Path,
    # )

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
        default=SYSTEMD_UNIT.name,
        help="Name of the unit file. "
             "It will get copied to the final destination "
             f"upon command completion: {SYSTEMD_UNIT.parent}.",
        metavar="OUTFILE",
        type=str,
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

    # Todo
    # ## STATUS
    #
    # subparser_status = systemd_subparsers.add_parser(
    #     name="status",
    #     formatter_class=_formatter,
    #     help="Systemd unit status.",
    # )
    #
    # ## JOURNALCTL
    #
    # subparser_journalctl = systemd_subparsers.add_parser(
    #     name="journalctl",
    #     formatter_class=_formatter,
    #     help="Follow logs.",
    # )

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
