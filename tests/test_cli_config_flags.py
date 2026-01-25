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


# --- Test suite for --read-url and its aliases ---


@pytest.mark.parametrize(
    "config_value, cli_args, expected_final_value",
    [
        # --- Precedence Tests ---
        (True, [], True),
        (False, [], False),
        (False, ["--read-url"], True),
        (True, ["--no-read-url"], False),
        (None, [], False),
        (None, ["--read-url"], True),
        (None, ["--no-read-url"], False),
        # --- Backward Compatibility Tests ---
        (False, ["--add-instapaper-url"], True),
        (True, ["--no-add-instapaper-url"], False),
        (None, ["--add-instapaper-url"], True),
    ],
    ids=[
        "config_true_no_cli",
        "config_false_no_cli",
        "config_false_cli_add",
        "config_true_cli_no_add",
        "no_config_no_cli",
        "no_config_cli_add",
        "no_config_cli_no_add",
        "bwc_config_false_cli_add",
        "bwc_config_true_cli_no_add",
        "bwc_no_config_cli_add",
    ],
)
def test_read_url_precedence_and_backward_compatibility(
    mock_auth,
    mock_client,
    mock_save,
    monkeypatch,
    config_value,
    cli_args,
    expected_final_value,
):
    """
    Tests the precedence and backward compatibility for the --read-url flag and its aliases.
    Precedence order: CLI Flag > Config File > Default (False).
    """
    argv = ["instapaper-scraper"] + cli_args
    monkeypatch.setattr("sys.argv", argv)

    config = None
    if config_value is not None:
        config = {"fields": {"read_url": config_value}}  # Updated key name here

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        with patch("builtins.input", return_value="0"):
            cli.main()

    mock_save.assert_called_once()
    saved_kwargs = mock_save.call_args.kwargs
    assert saved_kwargs["add_instapaper_url"] == expected_final_value
    assert saved_kwargs["add_article_preview"] is False


# --- Test suite for --article-preview and its aliases ---


@pytest.mark.parametrize(
    "config_value, cli_args, expected_final_value",
    [
        # --- Precedence Tests ---
        (True, [], True),
        (False, [], False),
        (False, ["--article-preview"], True),
        (True, ["--no-article-preview"], False),
        (None, [], False),
        (None, ["--article-preview"], True),
        (None, ["--no-article-preview"], False),
        # --- Backward Compatibility Tests ---
        (False, ["--add-article-preview"], True),
        (True, ["--no-add-article-preview"], False),
        (None, ["--add-article-preview"], True),
    ],
    ids=[
        "config_true_no_cli",
        "config_false_no_cli",
        "config_false_cli_add",
        "config_true_cli_no_add",
        "no_config_no_cli",
        "no_config_cli_add",
        "no_config_cli_no_add",
        "bwc_config_false_cli_add",
        "bwc_config_true_cli_no_add",
        "bwc_no_config_cli_add",
    ],
)
def test_article_preview_precedence_and_backward_compatibility(
    mock_auth,
    mock_client,
    mock_save,
    monkeypatch,
    config_value,
    cli_args,
    expected_final_value,
):
    """
    Tests the precedence and backward compatibility for the --article-preview flag and its aliases.
    Precedence order: CLI Flag > Config File > Default (False).
    """
    argv = ["instapaper-scraper"] + cli_args
    monkeypatch.setattr("sys.argv", argv)

    config = None
    if config_value is not None:
        config = {"fields": {"article_preview": config_value}}  # Updated key name here

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        with patch("builtins.input", return_value="0"):
            cli.main()

    mock_save.assert_called_once()
    saved_kwargs = mock_save.call_args.kwargs
    assert saved_kwargs["add_article_preview"] == expected_final_value
    assert saved_kwargs["add_instapaper_url"] is False
