import json

from click.testing import CliRunner

import rst_lsp.cli_server as cli


def test_cmnd_conf_file(temp_cwd, get_test_file_path):
    runner = CliRunner()
    result = runner.invoke(
        cli.cmnd_conf_file, ["--path", get_test_file_path("conf.py")]
    )
    assert result.exit_code == 0, result.output
    assert "SUCCESS" in result.output
    assert (temp_cwd / ".rst-lsp-db.json").exists()
    assert (temp_cwd / ".rst-lsp-db.json").stat().st_size > 0


def test_cmnd_source_file(temp_cwd, get_test_file_path):
    runner = CliRunner()
    result = runner.invoke(cli.cmnd_source_file, [get_test_file_path("test1.rst")])
    assert result.exit_code == 0, result.output
    assert "SUCCESS" in result.output
    assert (temp_cwd / ".rst-lsp-db.json").exists()
    assert (temp_cwd / ".rst-lsp-db.json").stat().st_size > 0


def test_cmnd_documents(temp_cwd, get_test_file_path):
    runner = CliRunner()
    result = runner.invoke(cli.cmnd_source_file, [get_test_file_path("test1.rst")])
    assert result.exit_code == 0, result.output
    result = runner.invoke(cli.cmnd_documents)
    assert result.exit_code == 0, result.output
    assert "test1.rst" in result.output


def test_cmnd_roles(temp_cwd, get_test_file_path, data_regression):
    runner = CliRunner()
    path = get_test_file_path("conf.py")
    result = runner.invoke(cli.cmnd_conf_file, ["--path", path])
    assert result.exit_code == 0, result.output
    result = runner.invoke(cli.cmnd_roles, ["-n", "index", "-n", "ref", "--raw"])
    assert result.exit_code == 0, result.output
    data_regression.check(json.loads(result.output))


def test_cmnd_directives(temp_cwd, get_test_file_path, data_regression):
    runner = CliRunner()
    result = runner.invoke(cli.cmnd_conf_file)
    assert result.exit_code == 0, result.output
    result = runner.invoke(cli.cmnd_directives, ["-n", "code", "--raw"])
    assert result.exit_code == 0, result.output
    data_regression.check(json.loads(result.output))


def test_cmnd_element(temp_cwd, get_test_file_path, data_regression):
    runner = CliRunner()
    path = get_test_file_path("test1.rst")
    result = runner.invoke(cli.cmnd_source_file, [path])
    result = runner.invoke(cli.cmnd_element, ["section", "--raw"])
    assert result.exit_code == 0, result.output
    data_regression.check(
        [{k: v for k, v in d.items() if k != "uri"} for d in json.loads(result.output)]
    )


def test_cmnd_lint(temp_cwd, get_test_file_path, data_regression):
    runner = CliRunner()
    path = get_test_file_path("test1.rst")
    result = runner.invoke(cli.cmnd_source_file, [path])
    result = runner.invoke(cli.cmnd_lint, [path, "--raw"])
    assert result.exit_code == 0, result.output
    data_regression.check(
        [{k: v for k, v in d.items() if k != "uri"} for d in json.loads(result.output)]
    )
