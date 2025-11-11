import unittest
import os
import stat
from unittest.mock import patch, mock_open
from cryptography.fernet import Fernet

# It's generally better to import the functions/classes you are testing
from scrape import get_encryption_key, run_instapaper_scraper

class TestEncryption(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        self.key_file = ".test_session_key"
        self.session_file = ".test_instapaper_session"
        # Clean up any old test files before each test
        if os.path.exists(self.key_file):
            os.remove(self.key_file)
        if os.path.exists(self.session_file):
            os.remove(self.session_file)

    def tearDown(self):
        """Tear down test environment."""
        if os.path.exists(self.key_file):
            os.remove(self.key_file)
        if os.path.exists(self.session_file):
            os.remove(self.session_file)

    def test_get_encryption_key_creates_file(self):
        """Test that a key file is created with correct permissions."""
        key = get_encryption_key(self.key_file)
        self.assertTrue(os.path.exists(self.key_file))
        
        # Check file permissions
        file_mode = os.stat(self.key_file).st_mode
        self.assertEqual(file_mode & (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO), stat.S_IRUSR | stat.S_IWUSR)
        
        # Test that calling it again returns the same key
        key2 = get_encryption_key(self.key_file)
        self.assertEqual(key, key2)

    @patch.dict(os.environ, {"INSTAPAPER_USERNAME": "", "INSTAPAPER_PASSWORD": ""})
    @patch('scrape.requests.Session')
    @patch('scrape.getpass.getpass')
    @patch('builtins.input')
    def test_session_file_is_encrypted_and_decrypted(self, mock_input, mock_getpass, mock_session_cls):
        """
        Test that the session file is written in an encrypted format
        and can be successfully decrypted on a subsequent run.
        """
        # --- First run: Login and save session ---
        from requests.cookies import create_cookie, RequestsCookieJar

        # Mock user input and login success
        mock_input.return_value = "testuser"
        mock_getpass.return_value = "testpass"
        
        mock_session = mock_session_cls.return_value
        mock_session.post.return_value.url = "/u"
        
        # Mock cookies being set after login.
        # The mock session needs a real cookie jar to be iterable and have items.
        mock_session.cookies = RequestsCookieJar()
        mock_session.cookies.set_cookie(create_cookie(name='pfu', value='test_pfu', domain='.instapaper.com'))
        mock_session.cookies.set_cookie(create_cookie(name='pfp', value='test_pfp', domain='.instapaper.com'))
        mock_session.cookies.set_cookie(create_cookie(name='pfh', value='test_pfh', domain='.instapaper.com'))

        # Mock the main loop to prevent it from running forever
        with patch('scrape.Application.at') as mock_app:
            # Make the first call to GetArticleIDs return has_more=False
            mock_app.return_value.result = ([], [], False)
            
            # Run the scraper, passing the test file names
            run_instapaper_scraper(session_file=self.session_file, key_file=self.key_file)

        # Verify that the session file was written
        self.assertTrue(os.path.exists(self.session_file))

        # Verify the content is encrypted
        with open(self.session_file, 'rb') as f:
            encrypted_data = f.read()
        
        key = get_encryption_key(self.key_file)
        fernet = Fernet(key)
        
        # This should not raise an exception if it's valid Fernet format
        decrypted_data = fernet.decrypt(encrypted_data).decode('utf-8')
        self.assertIn("pfu:test_pfu:.instapaper.com", decrypted_data)

        # --- Second run: Load from encrypted session ---

        # Reset mocks for the second run
        mock_session_cls.reset_mock()
        mock_session = mock_session_cls.return_value
        mock_session.cookies = RequestsCookieJar() # Give it a cookie jar for loading into
        
        # Mock the verification request to show we are logged in
        mock_session.get.return_value.text = "logged in page"

        with patch('scrape.Application.at') as mock_app:
            mock_app.return_value.result = ([], [], False)
            # Run scraper again; it should now load from the created session file
            run_instapaper_scraper(session_file=self.session_file, key_file=self.key_file)

        # Check that the session cookies were loaded correctly
        # This is an indirect check, but we can see if the login flow was skipped.
        mock_session.post.assert_not_called() # Login post should not be called
        
        # Check that the loaded cookies are in the session
        self.assertEqual(len(mock_session.cookies), 3)
        self.assertEqual(mock_session.cookies['pfu'], 'test_pfu')


if __name__ == '__main__':
    unittest.main()
