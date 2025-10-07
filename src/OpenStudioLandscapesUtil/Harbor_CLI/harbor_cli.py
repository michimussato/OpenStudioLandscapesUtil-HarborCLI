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
import configparser
import os
import pathlib
import shutil
import subprocess
import tarfile
import typing
from subprocess import CompletedProcess
from typing import Union, Any, Callable

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

HARBOR_URL: str = "https://github.com/goharbor/harbor/releases/download/v2.12.2/harbor-online-installer-v2.12.2.tgz"
HARBOR_ROOT_DIR: pathlib.Path = pathlib.Path("~/git/repos/OpenStudioLandscapes/.harbor").expanduser().resolve()
HARBOR_DOWNLOAD_DIR: pathlib.Path = HARBOR_ROOT_DIR.joinpath("download")
HARBOR_BIN_DIR: pathlib.Path = HARBOR_ROOT_DIR.joinpath("bin")
HARBOR_DATA_DIR: pathlib.Path = HARBOR_ROOT_DIR.joinpath("data")
HARBOR_CONFIG_ROOT: pathlib.Path = HARBOR_BIN_DIR
HARBOR_PREPARE: pathlib.Path = HARBOR_BIN_DIR.joinpath("prepare")

OPENSTUDIOLANDSCAPES__DOMAIN_LAN: str = "farm.evil"
OPENSTUDIOLANDSCAPES__HARBOR_HOSTNAME: str = "harbor.{OPENSTUDIOLANDSCAPES__DOMAIN_LAN}".format(OPENSTUDIOLANDSCAPES__DOMAIN_LAN=OPENSTUDIOLANDSCAPES__DOMAIN_LAN)
OPENSTUDIOLANDSCAPES__HARBOR_PORT: int = 80
OPENSTUDIOLANDSCAPES__HARBOR_PASSWORD: str = "Harbor12345"

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


class HarborCLIError(Exception):
    pass


# ---- Python API ----
# The functions defined in this section can be imported by users in their
# Python scripts/interactive interpreter, e.g. via
# `from OpenStudioLandscapesUtil.Harbor_CLI.harbor_cli import fib`,
# when using this Python module as a library.


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
        print(list(extract_to.iterdir()))
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


# @run.command()
# @click.option(
#     "--out-dir",
#     type=pathlib.Path,
#     default=HARBOR_CONFIG_ROOT,
#     show_default=True,
#     help="Full Path where the harbor.yml will be saved.",
#     required=True,
#     prompt=True,
# )
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


# @run.command()
# @click.option(
#     "--prepare-script",
#     type=pathlib.Path,
#     default=HARBOR_PREPARE,
#     show_default=True,
#     help="Full Path to the Harbor prepare script.",
#     required=True,
#     prompt=True,
# )
def prepare(
        prepare_script: pathlib.Path,
        config_file: pathlib.Path,
) -> CompletedProcess[bytes]:
    """Step 4"""

    prepare_script = prepare_script.expanduser().resolve()

    _logger.debug(prepare_script)

    if not prepare_script.exists():
        raise FileNotFoundError("`prepare` file not found. Not able to continue.")

    # if not HARBOR_CONFIG_ROOT.joinpath("harbor.yml").exists():
    if not config_file.exists():
        raise HarborCLIError(
            f"`harbor.yml` file not found at {config_file.as_posix()}. "
            f"Run `openstudiolandscapesutil-harborcli configure`."
        )

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
        "--conf",
        config_file.as_posix(),
    ]

    _logger.debug(f"{' '.join(bash_c)} \"{' '.join(cmd_prepare)}\"")

    ret = subprocess.run(
        [
            *bash_c,
            ' '.join(cmd_prepare),
        ],
        # f"{' '.join(bash_c)} \"{' '.join(cmd_prepare)}\"",
        shell=True,
        check=True,
    )

    return ret


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


# @run.command()
# # @click.option(
# #     "--install",
# #     is_flag=True,
# #     # type=pathlib.Path,
# #     # default=HARBOR_PREPARE,
# #     # show_default=True,
# #     help="Install systemd unit.",
# #     required=True,
# #     # prompt=True,
# # )
# @click.option(
#     "--enable",
#     is_flag=True,
#     help="Enable systemd unit.",
#     required=False,
# )
# @click.option(
#     "--start",
#     is_flag=True,
#     help="Start systemd unit.",
#     required=False,
# )
def systemd_install(
        enable: bool,
        start: bool,
        # install: bool,
) -> list[str | Any]:
    """Step 5"""

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

    unit_file_tmp = HARBOR_BIN_DIR.joinpath(SYSTEMD_UNIT.name)

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
        *SU_METHOD,
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
    _logger.info(f"\n{' '.join(sudo_bash_c)} \"{' '.join(install_service)}\"")

    return cmd


# @run.command()
# # @click.option(
# #     "--install",
# #     is_flag=True,
# #     # type=pathlib.Path,
# #     # default=HARBOR_PREPARE,
# #     # show_default=True,
# #     help="Install systemd unit.",
# #     required=True,
# #     # prompt=True,
# # )
# @click.option(
#     "--disable",
#     is_flag=True,
#     help="Disable systemd unit.",
#     required=False,
# )
# @click.option(
#     "--stop",
#     is_flag=True,
#     help="Stop systemd unit.",
#     required=True,
# )
# @click.option(
#     "--remove",
#     is_flag=True,
#     help="Remove systemd unit.",
#     required=False,
# )
def systemd_uninstall(
        disable: bool,
        stop: bool,
        remove: bool,
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
        SYSTEMD_UNIT.name,
    ]

    systemctl_stop = [
        shutil.which("systemctl"),
        "stop",
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
        *systemctl_stop,
    ]

    if disable:
        uninstall_service.extend(
            [
                "&&",
                *systemctl_disable
            ]
        )

    if remove:
        uninstall_service.extend(
            [
                "&&",
                *remove_service
            ]
        )

        uninstall_service.extend(
            [
                "&&",
                *daemon_reload,
            ]
        )

    _logger.debug(f"{uninstall_service = }")

    sudo_bash_c = [
        *SU_METHOD,
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
    _logger.info(f"\n{' '.join(sudo_bash_c)} \"{' '.join(uninstall_service)}\"")

    return cmd


# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.


def eval_(
        args: argparse.Namespace,
) -> Union[pathlib.Path, subprocess.CompletedProcess, None]:

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

        elif args.prepare_command == "run":
            result: subprocess.CompletedProcess = _cli_run(args)
            _logger.debug(f"{result = }")
            return result

    elif args.command == "systemd":
        pass


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


def _cli_run(
        args: argparse.Namespace,
) -> subprocess.CompletedProcess:

    result: subprocess.CompletedProcess = prepare(
        prepare_script=args.prepare_script,
        config_file=args.config_file,
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
        description="A tool to generate a README.md",
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
        default=pathlib.Path().cwd(),
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
        default=pathlib.Path().cwd(),
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
        # default=None,
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
        # "-c",
        dest="dry_run",
        action="store_true",
        required=False,
        default=False,
        help="Print the configuration to stdout.",
        # metavar="CLEAR",
        # type=bool,
    )

    mutex_configure.add_argument(
        "--destination-directory",
        "-d",
        dest="destination_directory",
        required=False,
        default=pathlib.Path().cwd(),
        help="Directory where to save the harbor.yml file.",
        metavar="DESTINATION_DIRECTORY",
        type=pathlib.Path,
    )

    subparser_configure.add_argument(
        "--overwrite",
        # "-c",
        dest="overwrite",
        action="store_true",
        required=False,
        default=False,
        help="Force overwriting existing harbor.yml file.",
        # metavar="CLEAR",
        # type=bool,
    )

    ## PREPARE

    subparser_run_prepare = prepare_subparsers.add_parser(
        name="run",
        formatter_class=_formatter,
    )

    subparser_run_prepare.add_argument(
        "--prepare-script",
        "-s",
        dest="prepare_script",
        required=True,
        default=pathlib.Path().cwd().joinpath("prepare"),
        help="Full path to the extracted prepare script.",
        metavar="PREPARE_SCRIPT",
        type=pathlib.Path,
    )

    subparser_run_prepare.add_argument(
        "--config-file",
        "-c",
        dest="config_file",
        required=False,
        default=pathlib.Path().cwd().joinpath("harbor.yml"),
        help="Full path to the harbor.yml config file.",
        metavar="CONFIG_FILE",
        type=pathlib.Path,
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
    # from pprint import pprint
    # pprint(args, indent=2)
    args: argparse.Namespace = parse_args(args)
    # pprint(vars(args), indent=2)
    # setup_logging(args)
    setup_logging(args)
    # _logger.debug("Starting crazy calculations...")
    eval_(args)
    # _logger.info("Script ends here")


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
