from unittest.mock import patch, MagicMock
from instapaper_scraper.cli import main


@patch("instapaper_scraper.cli.InstapaperAuthenticator")
@patch("instapaper_scraper.cli.InstapaperClient")
@patch("instapaper_scraper.cli.save_articles")
@patch("instapaper_scraper.cli.load_config")
def test_main_with_liked_folder_arg(
    mock_load_config, mock_save_articles, mock_client, mock_authenticator
):
    """Test main function with '--folder liked' argument."""
    mock_load_config.return_value = {"folders": []}
    mock_auth_instance = MagicMock()
    mock_auth_instance.login.return_value = True
    mock_authenticator.return_value = mock_auth_instance

    mock_client_instance = MagicMock()
    mock_client.return_value = mock_client_instance

    test_args = ["instapaper-scraper", "--folder", "liked"]

    with patch("sys.argv", test_args):
        main()

    # Verify that get_all_articles was called with the correct folder_info
    mock_client_instance.get_all_articles.assert_called_once()
    call_args, call_kwargs = mock_client_instance.get_all_articles.call_args
    assert call_kwargs.get("folder_info") == {"id": "liked"}


@patch("instapaper_scraper.cli.InstapaperAuthenticator")
@patch("instapaper_scraper.cli.InstapaperClient")
@patch("instapaper_scraper.cli.save_articles")
@patch("instapaper_scraper.cli.load_config")
def test_main_with_archive_folder_arg(
    mock_load_config, mock_save_articles, mock_client, mock_authenticator
):
    """Test main function with '--folder archive' argument."""
    mock_load_config.return_value = {"folders": []}
    mock_auth_instance = MagicMock()
    mock_auth_instance.login.return_value = True
    mock_authenticator.return_value = mock_auth_instance

    mock_client_instance = MagicMock()
    mock_client.return_value = mock_client_instance

    test_args = ["instapaper-scraper", "--folder", "archive"]

    with patch("sys.argv", test_args):
        main()

    # Verify that get_all_articles was called with the correct folder_info
    mock_client_instance.get_all_articles.assert_called_once()
    call_args, call_kwargs = mock_client_instance.get_all_articles.call_args
    assert call_kwargs.get("folder_info") == {"id": "archive"}


@patch("builtins.input", MagicMock(return_value="1"))
@patch("instapaper_scraper.cli.InstapaperAuthenticator")
@patch("instapaper_scraper.cli.InstapaperClient")
@patch("instapaper_scraper.cli.save_articles")
@patch("instapaper_scraper.cli.load_config")
def test_main_interactive_liked(
    mock_load_config, mock_save_articles, mock_client, mock_authenticator
):
    """Test main function with interactive selection of 'Liked' folder."""
    mock_load_config.return_value = {"folders": [{"key": "test"}]}
    mock_auth_instance = MagicMock()
    mock_auth_instance.login.return_value = True
    mock_authenticator.return_value = mock_auth_instance

    mock_client_instance = MagicMock()
    mock_client.return_value = mock_client_instance

    test_args = ["instapaper-scraper"]

    with patch("sys.argv", test_args):
        main()

    # Verify that get_all_articles was called with the correct folder_info
    mock_client_instance.get_all_articles.assert_called_once()
    call_args, call_kwargs = mock_client_instance.get_all_articles.call_args
    assert call_kwargs.get("folder_info") == {"id": "liked"}


@patch("builtins.input", MagicMock(return_value="2"))
@patch("instapaper_scraper.cli.InstapaperAuthenticator")
@patch("instapaper_scraper.cli.InstapaperClient")
@patch("instapaper_scraper.cli.save_articles")
@patch("instapaper_scraper.cli.load_config")
def test_main_interactive_archive(
    mock_load_config, mock_save_articles, mock_client, mock_authenticator
):
    """Test main function with interactive selection of 'Archive' folder."""
    mock_load_config.return_value = {"folders": [{"key": "test"}]}
    mock_auth_instance = MagicMock()
    mock_auth_instance.login.return_value = True
    mock_authenticator.return_value = mock_auth_instance

    mock_client_instance = MagicMock()
    mock_client.return_value = mock_client_instance

    test_args = ["instapaper-scraper"]

    with patch("sys.argv", test_args):
        main()

    # Verify that get_all_articles was called with the correct folder_info
    mock_client_instance.get_all_articles.assert_called_once()
    call_args, call_kwargs = mock_client_instance.get_all_articles.call_args
    assert call_kwargs.get("folder_info") == {"id": "archive"}


@patch("instapaper_scraper.cli.InstapaperAuthenticator")
@patch("instapaper_scraper.cli.InstapaperClient")
@patch("instapaper_scraper.cli.save_articles")
@patch("instapaper_scraper.cli.load_config")
def test_main_liked_folder_with_custom_filename(
    mock_load_config, mock_save_articles, mock_client, mock_authenticator
):
    """Test that liked_output_filename from config is used."""
    mock_load_config.return_value = {"liked_output_filename": "my-liked-stuff.json"}
    mock_auth_instance = MagicMock()
    mock_auth_instance.login.return_value = True
    mock_authenticator.return_value = mock_auth_instance

    mock_client_instance = MagicMock()
    mock_client_instance.get_all_articles.return_value = []
    mock_client.return_value = mock_client_instance

    test_args = ["instapaper-scraper", "--folder", "liked", "--format", "json"]

    with patch("sys.argv", test_args):
        main()

    mock_save_articles.assert_called_once_with(
        [],
        "json",
        "my-liked-stuff.json",
        add_instapaper_url=False,
        add_article_preview=False,
    )


@patch("instapaper_scraper.cli.InstapaperAuthenticator")
@patch("instapaper_scraper.cli.InstapaperClient")
@patch("instapaper_scraper.cli.save_articles")
@patch("instapaper_scraper.cli.load_config")
def test_main_archive_folder_with_custom_filename(
    mock_load_config, mock_save_articles, mock_client, mock_authenticator
):
    """Test that archive_output_filename from config is used."""
    mock_load_config.return_value = {"archive_output_filename": "my-archive.db"}
    mock_auth_instance = MagicMock()
    mock_auth_instance.login.return_value = True
    mock_authenticator.return_value = mock_auth_instance

    mock_client_instance = MagicMock()
    mock_client_instance.get_all_articles.return_value = []
    mock_client.return_value = mock_client_instance

    test_args = ["instapaper-scraper", "--folder", "archive", "--format", "sqlite"]

    with patch("sys.argv", test_args):
        main()

    mock_save_articles.assert_called_once_with(
        [],
        "sqlite",
        "my-archive.db",
        add_instapaper_url=False,
        add_article_preview=False,
    )
