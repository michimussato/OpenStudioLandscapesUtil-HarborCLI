import argparse
import pathlib
import shutil
import textwrap
import requests

import pytest

import OpenStudioLandscapesUtil.Harbor_CLI.harbor_cli as harbor_cli

__author__ = "Michael Mussato"
__copyright__ = "Michael Mussato"
__license__ = "AGPL-3.0-or-later"


# Todo
#  - [ ] Set up logging
#        https://pytest-with-eric.com/pytest-best-practices/pytest-logging/


def harbor_yml_data() -> str:
    ret = textwrap.dedent(
        """\
        _version: 2.12.0
        cache:
          enabled: false
          expire_hours: 24
        data_volume: /home/michael/git/repos/OpenStudioLandscapesUtil-HarborCLI/.harbor/data
        database:
          conn_max_idle_time: 0
          max_idle_conns: 100
          max_open_conns: 900
          password: root123
        harbor_admin_password: Harbor12345
        hostname: harbor.openstudiolandscapes.lan
        http:
          port: 80
        jobservice:
          job_loggers:
          - STD_OUTPUT
          - FILE
          logger_sweeper_duration: 1
          max_job_workers: 10
        log:
          level: info
          local:
            location: /var/log/harbor
            rotate_count: 50
            rotate_size: 200M
        notification:
          webhook_job_http_client_timeout: 3
          webhook_job_max_retry: 3
        proxy:
          components:
          - core
          - jobservice
          - trivy
          http_proxy: null
          https_proxy: null
          no_proxy: null
        trivy:
          ignore_unfixed: false
          insecure: false
          offline_scan: false
          security_check: vuln
          skip_java_db_update: false
          skip_update: false
          timeout: 5m0s
        upload_purging:
          age: 168h
          dryrun: false
          enabled: true
          interval: 24h
        """
    )

    return ret


def test_auth_tokenized():
    expected = "YWRtaW46SGFyYm9yMTIzNDU="

    result = harbor_cli.auth_tokenized(
        user="admin",
        password="Harbor12345",
    )

    assert result == expected


def test_configure():
    expected: pathlib.Path = pathlib.Path(__file__).parent.joinpath("harbor.yml")

    result: pathlib.Path = harbor_cli.configure(
        destination_directory=pathlib.Path(__file__).parent,
        overwrite=True,
        harbor_yml_data=harbor_yml_data(),
    )

    assert result == expected


def test__configure_default():
    args: argparse.Namespace = argparse.Namespace()
    args.host = "harbor.openstudiolandscapes.lan"
    args.password = "Harbor12345"
    args.port = "80"
    args.harbor_root_dir = pathlib.Path(__file__).parent
    args.harbor_data = harbor_cli.OPENSTUDIOLANDSCAPES__HARBOR_DATA_DIR

    expected: str = textwrap.dedent(
        """\
        _version: 2.12.0
        cache:
          enabled: false
          expire_hours: 24
        data_volume: /home/michael/git/repos/OpenStudioLandscapesUtil-HarborCLI/tests/data
        database:
          conn_max_idle_time: 0
          max_idle_conns: 100
          max_open_conns: 900
          password: root123
        harbor_admin_password: Harbor12345
        hostname: harbor.openstudiolandscapes.lan
        http:
          port: '80'
        jobservice:
          job_loggers:
          - STD_OUTPUT
          - FILE
          logger_sweeper_duration: 1
          max_job_workers: 10
        log:
          level: info
          local:
            location: /var/log/harbor
            rotate_count: 50
            rotate_size: 200M
        notification:
          webhook_job_http_client_timeout: 3
          webhook_job_max_retry: 3
        proxy:
          components:
          - core
          - jobservice
          - trivy
          http_proxy: null
          https_proxy: null
          no_proxy: null
        trivy:
          ignore_unfixed: false
          insecure: false
          offline_scan: false
          security_check: vuln
          skip_java_db_update: false
          skip_update: false
          timeout: 5m0s
        upload_purging:
          age: 168h
          dryrun: false
          enabled: true
          interval: 24h
        """
    )

    result: str = harbor_cli._configure(
        args=args,
    )

    assert result == expected


def test__configure_non_default():
    args: argparse.Namespace = argparse.Namespace()
    args.host = "harbor1.anydomain.org"
    args.password = "AsDf"
    args.port = "88"
    args.harbor_root_dir = pathlib.Path(__file__).parent
    args.harbor_data = "data"

    expected: str = textwrap.dedent(
        """\
        _version: 2.12.0
        cache:
          enabled: false
          expire_hours: 24
        data_volume: /home/michael/git/repos/OpenStudioLandscapesUtil-HarborCLI/tests/data
        database:
          conn_max_idle_time: 0
          max_idle_conns: 100
          max_open_conns: 900
          password: root123
        harbor_admin_password: AsDf
        hostname: harbor1.anydomain.org
        http:
          port: '88'
        jobservice:
          job_loggers:
          - STD_OUTPUT
          - FILE
          logger_sweeper_duration: 1
          max_job_workers: 10
        log:
          level: info
          local:
            location: /var/log/harbor
            rotate_count: 50
            rotate_size: 200M
        notification:
          webhook_job_http_client_timeout: 3
          webhook_job_max_retry: 3
        proxy:
          components:
          - core
          - jobservice
          - trivy
          http_proxy: null
          https_proxy: null
          no_proxy: null
        trivy:
          ignore_unfixed: false
          insecure: false
          offline_scan: false
          security_check: vuln
          skip_java_db_update: false
          skip_update: false
          timeout: 5m0s
        upload_purging:
          age: 168h
          dryrun: false
          enabled: true
          interval: 24h
        """
    )

    result: str = harbor_cli._configure(
        args=args,
    )

    assert result == expected


def test_systemd_unit_dict():
    expected = {'Unit': {'Description': 'Harbor for OpenStudioLandscapes', 'Documentation': 'https://github.com/michimussato/OpenStudioLandscapes/blob/main/wiki/guides/harbor.md'},
                'Service': {'Type': 'simple', 'User': 'root', 'Group': 'root', 'Restart': 'always',
                            'WorkingDirectory': '/home/michael/git/repos/OpenStudioLandscapesUtil-HarborCLI/tests',
                            'ExecStart': '/usr/local/bin/docker compose --progress plain --file /home/michael/git/repos/OpenStudioLandscapesUtil-HarborCLI/tests/bin/docker-compose.yml --project-name openstudiolandscapes-harbor up --remove-orphans',
                            'ExecReload': '/usr/local/bin/docker compose --progress plain --file /home/michael/git/repos/OpenStudioLandscapesUtil-HarborCLI/tests/bin/docker-compose.yml --project-name openstudiolandscapes-harbor restart',
                            'ExecStop': '/usr/local/bin/docker compose --progress plain --file /home/michael/git/repos/OpenStudioLandscapesUtil-HarborCLI/tests/bin/docker-compose.yml --project-name openstudiolandscapes-harbor down'},
                'Install': {'WantedBy': 'multi-user.target'}}

    _cmd_harbor = [
        shutil.which("docker"),
        "compose",
        "--progress",
        harbor_cli.DOCKER_PROGRESS[2],
        "--file",
        pathlib.Path(__file__).parent.joinpath(harbor_cli.OPENSTUDIOLANDSCAPES__HARBOR_BIN_DIR, "docker-compose.yml").as_posix(),
        "--project-name",
        "openstudiolandscapes-harbor",
    ]

    result = harbor_cli.systemd_unit_dict(
        working_directory=pathlib.Path(__file__).parent,
        exec_start=[
            *_cmd_harbor,
            "up",
            "--remove-orphans",
        ],
        exec_reload=[
            *_cmd_harbor,
            "restart",
        ],
        exec_stop=[
            *_cmd_harbor,
            "down",
        ]
    )

    assert result == expected


def test_systemd_install():
    expected: list = [
        '/usr/bin/sudo',
        '--user=root',
        '/usr/bin/bash',
        '-c',
        '/usr/bin/cp '
        '/home/michael/git/repos/OpenStudioLandscapesUtil-HarborCLI/tests/harbor.unit '
        '/usr/lib/systemd/system/harbor.service && /usr/bin/chmod 644 '
        '/usr/lib/systemd/system/harbor.service && /usr/bin/systemctl daemon-reload '
        '&& /usr/bin/systemctl start harbor.service && /usr/bin/systemctl enable '
        'harbor.service',
    ]

    _cmd_harbor = [
        shutil.which("docker"),
        "compose",
        "--progress",
        harbor_cli.DOCKER_PROGRESS[2],
        "--file",
        pathlib.Path(__file__).parent.joinpath(harbor_cli.OPENSTUDIOLANDSCAPES__HARBOR_BIN_DIR, "docker-compose.yml").as_posix(),
        "--project-name",
        "openstudiolandscapes-harbor",
    ]

    result = harbor_cli.systemd_install(
        su_method="sudo",
        outfile=pathlib.Path(__file__).parent.joinpath("harbor.unit"),
        start=True,
        enable=True,
        harbor_bin_dir=pathlib.Path(__file__).parent,
    )

    assert result == expected


def test_systemd_uninstall():
    expected: list = [
        '/usr/bin/sudo',
        '--user=root',
        '/usr/bin/bash',
        '-c',
        '/usr/bin/systemctl disable --now harbor.service && /usr/bin/rm '
        '/usr/lib/systemd/system/harbor.service && /usr/bin/systemctl daemon-reload',
    ]

    result = harbor_cli.systemd_uninstall(
        su_method="sudo",
        disable=True,
        stop=True,
        uninstall=True,
    )

    assert result == expected


def test_systemd_status():
    expected: list = [
        '/usr/bin/bash',
        '-c',
        '/usr/bin/systemctl --full --no-pager harbor.service',
    ]

    result = harbor_cli.systemd_status()

    assert result == expected


def test_systemd_journalctl():
    expected: list = [
        '/usr/bin/bash',
        '-c',
        '/usr/bin/journalctl --follow --unit harbor.service',
    ]

    result = harbor_cli.systemd_journalctl()

    assert result == expected


def test_project_create():
    expected: list = [
        '/usr/bin/curl',
        '-X',
        'POST',
        '-H "accept: application/json"',
        '-H "authorization: Basic YWRtaW46SGFyYm9yMTIzNDU="',
        '-H "X-Resource-Name-In-Location: false"',
        '-H "Content-Type: application/json"',
        '-H "Content-Length: 53"',
        '-d',
        '\'{"project_name": "my-harbor-project", "public": true}\'',
        "'http://harbor.openstudiolandscapes.lan:80/api/v2.0/projects'",
    ]

    result = harbor_cli.project_create(
        host="harbor.openstudiolandscapes.lan",
        port=80,
        user="admin",
        password="Harbor12345",
        project_name="my-harbor-project",
    )

    assert result == expected


def test_project_delete():
    expected: list = [
        '/usr/bin/curl',
        '-X',
        'DELETE',
        '-H "accept: application/json"',
        '-H "X-Is-Resource-Name: false"',
        '-H "authorization: Basic YWRtaW46SGFyYm9yMTIzNDU="',
        '-H "Content-Length: 0"',
        "'http://harbor.openstudiolandscapes.lan:80/api/v2.0/projects/my-harbor-project'",
    ]

    result = harbor_cli.project_delete(
        host="harbor.openstudiolandscapes.lan",
        port=80,
        user="admin",
        password="Harbor12345",
        project_name="my-harbor-project",
    )

    assert result == expected


@pytest.mark.skip("Todo")
def test_download():
    pass


@pytest.mark.skip("Todo")
def test_extract():
    pass


@pytest.mark.skip("Todo")
def test_prepare():
    pass


def test_curlify():
    expected = [
        '/usr/bin/curl',
        '-X',
        'POST',
        '-H "accept: application/json"',
        '-H "authorization: Basic YWRtaW46SGFyYm9yMTIzNDU="',
        '-H "X-Resource-Name-In-Location: false"',
        '-H "Content-Type: application/json"',
        '-H "Content-Length: 58"',
        '-d',
        '\'{"project_name": "my-harbor-test-project", "public": true}\'',
        "'http://harbor.openstudiolandscapes.wan:99/api/v2.0/projects'",
    ]

    project_name_ = "my-harbor-test-project"

    host="harbor.openstudiolandscapes.wan"
    port = 99

    _project_create_dict: dict = {
        "endpoint": f"http://{host}:{port}{harbor_cli.OPENSTUDIOLANDSCAPES__HARBOR_API_ENDPOINT}/projects",
        "method": harbor_cli.RequestMethod.POST.value,
        "headers": {
            "accept": "application/json",
            "authorization": f"Basic {harbor_cli.auth_tokenized(user='admin', password='Harbor12345')}",
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
        # return _project_create_dict
    request: requests.Request = requests.Request(
        method=_project_create_dict["method"],
        url=_project_create_dict["endpoint"],
        headers=_project_create_dict["headers"],
        **_project_create_dict["payload"],
    )

    prepared_request: requests.PreparedRequest = request.prepare()

    result = harbor_cli.curlify(request=prepared_request)

    assert result == expected


# Todo
#  - [ ] capsys tests
# def test_fib():
#     """API Tests"""
#     assert fib(1) == 1
#     assert fib(2) == 1
#     assert fib(7) == 13
#     with pytest.raises(AssertionError):
#         fib(-10)
#
#
# def test_main(capsys):
#     """CLI Tests"""
#     # capsys is a pytest fixture that allows asserts against stdout/stderr
#     # https://docs.pytest.org/en/stable/capture.html
#     main(["7"])
#     captured = capsys.readouterr()
#     assert "The 7-th Fibonacci number is 13" in captured.out
