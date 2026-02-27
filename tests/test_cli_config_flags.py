import pytest
from unittest.mock import MagicMock, patch
from instapaper_scraper import cli


# Fixtures to mock dependencies, making tests focused and fast.
@pytest.fixture
def mock_auth(monkeypatch):
    """Fixture to mock the InstapaperAuthenticator."""
    mock = MagicMock()
    # Assume login is always successful for these tests
    mock.return_value.login.return_value = True
    monkeypatch.setattr("instapaper_scraper.cli.InstapaperAuthenticator", mock)
    return mock


@pytest.fixture
def mock_client(monkeypatch):
    """Fixture to mock the InstapaperClient."""
    mock = MagicMock()
    # Assume no articles are returned to speed up the test
    mock.return_value.get_all_articles.return_value = []
    monkeypatch.setattr("instapaper_scraper.cli.InstapaperClient", mock)
    return mock


@pytest.fixture
def mock_save(monkeypatch):
    """Fixture to mock the save_articles function."""
    mock = MagicMock()
    monkeypatch.setattr("instapaper_scraper.cli.save_articles", mock)
    return mock


# --- Test suite for boolean flags with precedence and backward compatibility ---


@pytest.mark.parametrize(
    "flag_details, config_value, cli_args, expected_final_value",
    [
        # --read-url cases
        (
            (
                "read_url",
                "add_instapaper_url",
                "--read-url",
                "--no-read-url",
                "--add-instapaper-url",
                "--no-add-instapaper-url",
            ),
            True,
            [],
            True,
        ),
        (
            (
                "read_url",
                "add_instapaper_url",
                "--read-url",
                "--no-read-url",
                "--add-instapaper-url",
                "--no-add-instapaper-url",
            ),
            False,
            [],
            False,
        ),
        (
            (
                "read_url",
                "add_instapaper_url",
                "--read-url",
                "--no-read-url",
                "--add-instapaper-url",
                "--no-add-instapaper-url",
            ),
            False,
            ["--read-url"],
            True,
        ),
        (
            (
                "read_url",
                "add_instapaper_url",
                "--read-url",
                "--no-read-url",
                "--add-instapaper-url",
                "--no-add-instapaper-url",
            ),
            True,
            ["--no-read-url"],
            False,
        ),
        (
            (
                "read_url",
                "add_instapaper_url",
                "--read-url",
                "--no-read-url",
                "--add-instapaper-url",
                "--no-add-instapaper-url",
            ),
            None,
            [],
            False,
        ),
        (
            (
                "read_url",
                "add_instapaper_url",
                "--read-url",
                "--no-read-url",
                "--add-instapaper-url",
                "--no-add-instapaper-url",
            ),
            None,
            ["--read-url"],
            True,
        ),
        (
            (
                "read_url",
                "add_instapaper_url",
                "--read-url",
                "--no-read-url",
                "--add-instapaper-url",
                "--no-add-instapaper-url",
            ),
            None,
            ["--no-read-url"],
            False,
        ),
        (
            (
                "read_url",
                "add_instapaper_url",
                "--read-url",
                "--no-read-url",
                "--add-instapaper-url",
                "--no-add-instapaper-url",
            ),
            False,
            ["--add-instapaper-url"],
            True,
        ),
        (
            (
                "read_url",
                "add_instapaper_url",
                "--read-url",
                "--no-read-url",
                "--add-instapaper-url",
                "--no-add-instapaper-url",
            ),
            True,
            ["--no-add-instapaper-url"],
            False,
        ),
        (
            (
                "read_url",
                "add_instapaper_url",
                "--read-url",
                "--no-read-url",
                "--add-instapaper-url",
                "--no-add-instapaper-url",
            ),
            None,
            ["--add-instapaper-url"],
            True,
        ),
        # --article-preview cases
        (
            (
                "article_preview",
                "add_article_preview",
                "--article-preview",
                "--no-article-preview",
                "--add-article-preview",
                "--no-add-article-preview",
            ),
            True,
            [],
            True,
        ),
        (
            (
                "article_preview",
                "add_article_preview",
                "--article-preview",
                "--no-article-preview",
                "--add-article-preview",
                "--no-add-article-preview",
            ),
            False,
            [],
            False,
        ),
        (
            (
                "article_preview",
                "add_article_preview",
                "--article-preview",
                "--no-article-preview",
                "--add-article-preview",
                "--no-add-article-preview",
            ),
            False,
            ["--article-preview"],
            True,
        ),
        (
            (
                "article_preview",
                "add_article_preview",
                "--article-preview",
                "--no-article-preview",
                "--add-article-preview",
                "--no-add-article-preview",
            ),
            True,
            ["--no-article-preview"],
            False,
        ),
        (
            (
                "article_preview",
                "add_article_preview",
                "--article-preview",
                "--no-article-preview",
                "--add-article-preview",
                "--no-add-article-preview",
            ),
            None,
            [],
            False,
        ),
        (
            (
                "article_preview",
                "add_article_preview",
                "--article-preview",
                "--no-article-preview",
                "--add-article-preview",
                "--no-add-article-preview",
            ),
            None,
            ["--article-preview"],
            True,
        ),
        (
            (
                "article_preview",
                "add_article_preview",
                "--article-preview",
                "--no-article-preview",
                "--add-article-preview",
                "--no-add-article-preview",
            ),
            None,
            ["--no-article-preview"],
            False,
        ),
        (
            (
                "article_preview",
                "add_article_preview",
                "--article-preview",
                "--no-article-preview",
                "--add-article-preview",
                "--no-add-article-preview",
            ),
            False,
            ["--add-article-preview"],
            True,
        ),
        (
            (
                "article_preview",
                "add_article_preview",
                "--article-preview",
                "--no-article-preview",
                "--add-article-preview",
                "--no-add-article-preview",
            ),
            True,
            ["--no-add-article-preview"],
            False,
        ),
        (
            (
                "article_preview",
                "add_article_preview",
                "--article-preview",
                "--no-article-preview",
                "--add-article-preview",
                "--no-add-article-preview",
            ),
            None,
            ["--add-article-preview"],
            True,
        ),
    ],
    ids=[
        # read_url ids
        "read_url_config_true_no_cli",
        "read_url_config_false_no_cli",
        "read_url_config_false_cli_add",
        "read_url_config_true_cli_no_add",
        "read_url_no_config_no_cli",
        "read_url_no_config_cli_add",
        "read_url_no_config_cli_no_add",
        "read_url_bwc_config_false_cli_add",
        "read_url_bwc_config_true_cli_no_add",
        "read_url_bwc_no_config_cli_add",
        # article_preview ids
        "article_preview_config_true_no_cli",
        "article_preview_config_false_no_cli",
        "article_preview_config_false_cli_add",
        "article_preview_config_true_cli_no_add",
        "article_preview_no_config_no_cli",
        "article_preview_no_config_cli_add",
        "article_preview_no_config_cli_no_add",
        "article_preview_bwc_config_false_cli_add",
        "article_preview_bwc_config_true_cli_no_add",
        "article_preview_bwc_no_config_cli_add",
    ],
)
def test_flag_precedence_and_backward_compatibility(
    mock_auth,
    mock_client,
    mock_save,
    monkeypatch,
    flag_details,
    config_value,
    cli_args,
    expected_final_value,
):
    """
    Tests the precedence and backward compatibility for boolean flags.
    Precedence order: CLI Flag > Config File > Default (False).
    Supports both modern and backward-compatible flag names.
    """
    config_key, dest_key, pos_flag, neg_flag, bwc_pos_flag, bwc_neg_flag = flag_details

    argv = ["instapaper-scraper"] + cli_args
    monkeypatch.setattr("sys.argv", argv)

    config = None
    if config_value is not None:
        config = {"fields": {config_key: config_value}}

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        with patch("builtins.input", return_value="0"):
            cli.main()

    mock_save.assert_called_once()
    saved_kwargs = mock_save.call_args.kwargs
    assert saved_kwargs[dest_key] == expected_final_value

    # Verify the other flag is False
    other_dest_key = (
        "add_article_preview"
        if dest_key == "add_instapaper_url"
        else "add_instapaper_url"
    )
    assert saved_kwargs[other_dest_key] is False


@pytest.mark.parametrize(
    "config_data, cli_args, expected_format",
    [
        (None, [], "csv"),  # No config, no flag -> default "csv"
        ({"output": {"format": "json"}}, [], "json"),  # Config "json", no flag
        (
            {"output": {"format": "json"}},
            ["--format", "sqlite"],
            "sqlite",
        ),  # Config "json", flag "sqlite" -> "sqlite"
        (None, ["--format", "csv"], "csv"),  # No config, flag "csv"
        (
            {"output": {"format": "invalid"}},
            [],
            "csv",
        ),  # Invalid format in config -> fallback to "csv"
    ],
    ids=[
        "default_format",
        "format_from_config",
        "cli_overrides_config",
        "format_from_cli",
        "invalid_config_format",
    ],
)
def test_format_precedence(
    mock_auth,
    mock_client,
    mock_save,
    monkeypatch,
    config_data,
    cli_args,
    expected_format,
):
    """
    Tests the precedence for the output format setting.
    Precedence order: CLI Flag > Config File > Default ("csv").
    """
    argv = ["instapaper-scraper"] + cli_args
    monkeypatch.setattr("sys.argv", argv)

    with patch("instapaper_scraper.cli.load_config", return_value=config_data):
        with patch("builtins.input", return_value="0"):
            cli.main()

    mock_save.assert_called_once()
    saved_args = mock_save.call_args[0]
    assert saved_args[1] == expected_format
