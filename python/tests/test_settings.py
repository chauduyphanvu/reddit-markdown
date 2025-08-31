"""
Settings tests focusing on behavior, not implementation.
"""

import unittest
import tempfile
import os
import json

from settings import Settings


class TestSettingsBehavior(unittest.TestCase):
    """Test settings behavior and configuration outcomes."""

    def test_settings_load_successfully(self):
        """Settings should load from valid JSON file."""
        valid_config = {
            "version": "1.0.0",
            "file_format": "html",
            "show_upvotes": False,
            "filtered_message": "Content removed",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_config, f)
            temp_path = f.name

        try:
            settings = Settings(temp_path)

            # Verify settings were loaded correctly
            self.assertEqual(settings.version, "1.0.0")
            self.assertEqual(settings.file_format, "html")
            self.assertEqual(settings.show_upvotes, False)
            self.assertEqual(settings.filtered_message, "Content removed")
        finally:
            os.unlink(temp_path)

    def test_settings_provide_defaults(self):
        """Settings should provide sensible defaults for missing values."""
        minimal_config = {"version": "1.0.0"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(minimal_config, f)
            temp_path = f.name

        try:
            settings = Settings(temp_path)

            # Verify defaults are applied
            self.assertEqual(settings.file_format, "md")  # Default format
            self.assertEqual(settings.show_upvotes, True)  # Default behavior
            self.assertEqual(settings.filtered_message, "Filtered")  # Default message
            self.assertEqual(settings.filtered_keywords, [])  # Default empty list
            self.assertEqual(settings.filtered_authors, [])  # Default empty list
        finally:
            os.unlink(temp_path)

    def test_authentication_settings(self):
        """Authentication settings should come from environment variables."""
        auth_config = {"version": "1.0.0", "auth": {"login_on_startup": True}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(auth_config, f)
            temp_path = f.name

        try:
            # Set environment variables for auth credentials
            os.environ["REDDIT_CLIENT_ID"] = "env_client_123"
            os.environ["REDDIT_CLIENT_SECRET"] = "env_secret_456"
            os.environ["REDDIT_USERNAME"] = "env_user"
            os.environ["REDDIT_PASSWORD"] = "env_pass"

            settings = Settings(temp_path)

            # login_on_startup comes from JSON
            self.assertEqual(settings.login_on_startup, True)

            # Credentials come from environment variables
            self.assertEqual(settings.client_id, "env_client_123")
            self.assertEqual(settings.client_secret, "env_secret_456")
            self.assertEqual(settings.username, "env_user")
            self.assertEqual(settings.password, "env_pass")

        finally:
            # Clean up environment variables
            for var in [
                "REDDIT_CLIENT_ID",
                "REDDIT_CLIENT_SECRET",
                "REDDIT_USERNAME",
                "REDDIT_PASSWORD",
            ]:
                if var in os.environ:
                    del os.environ[var]
            os.unlink(temp_path)

    def test_filtering_configuration(self):
        """Filtering settings should be properly configured."""
        filter_config = {
            "version": "1.0.0",
            "filtered_message": "🚫 Blocked",
            "filters": {
                "keywords": ["spam", "advertisement", "promotion"],
                "min_upvotes": 10,
                "authors": ["banned_user1", "spam_account"],
                "regexes": [r"\b(buy|sell)\b", r"http[s]?://\S+"],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(filter_config, f)
            temp_path = f.name

        try:
            settings = Settings(temp_path)

            self.assertEqual(settings.filtered_message, "🚫 Blocked")
            self.assertEqual(
                settings.filtered_keywords, ["spam", "advertisement", "promotion"]
            )
            self.assertEqual(settings.filtered_min_upvotes, 10)
            self.assertEqual(
                settings.filtered_authors, ["banned_user1", "spam_account"]
            )
            self.assertEqual(
                settings.filtered_regexes, [r"\b(buy|sell)\b", r"http[s]?://\S+"]
            )
        finally:
            os.unlink(temp_path)

    def test_display_and_format_settings(self):
        """Display and formatting settings should control output appearance."""
        display_config = {
            "version": "1.0.0",
            "file_format": "html",
            "show_upvotes": False,
            "show_timestamp": False,
            "show_auto_mod_comment": True,
            "reply_depth_color_indicators": False,
            "reply_depth_max": 5,
            "line_break_between_parent_replies": False,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(display_config, f)
            temp_path = f.name

        try:
            settings = Settings(temp_path)

            self.assertEqual(settings.file_format, "html")
            self.assertEqual(settings.show_upvotes, False)
            self.assertEqual(settings.show_timestamp, False)
            self.assertEqual(settings.show_auto_mod_comment, True)
            self.assertEqual(settings.reply_depth_color_indicators, False)
            self.assertEqual(settings.reply_depth_max, 5)
            self.assertEqual(settings.line_break_between_parent_replies, False)
        finally:
            os.unlink(temp_path)

    def test_file_and_directory_settings(self):
        """File handling settings should control save behavior."""
        file_config = {
            "version": "1.0.0",
            "default_save_location": "/custom/save/path",
            "overwrite_existing_file": True,
            "save_posts_by_subreddits": True,
            "use_timestamped_directories": True,
            "enable_media_downloads": False,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(file_config, f)
            temp_path = f.name

        try:
            settings = Settings(temp_path)

            self.assertEqual(settings.default_save_location, "/custom/save/path")
            self.assertEqual(settings.overwrite_existing_file, True)
            self.assertEqual(settings.save_posts_by_subreddits, True)
            self.assertEqual(settings.use_timestamped_directories, True)
            self.assertEqual(settings.enable_media_downloads, False)
        finally:
            os.unlink(temp_path)

    def test_multireddit_configuration(self):
        """Multi-reddit settings should be properly loaded."""
        multi_config = {
            "version": "1.0.0",
            "multi_reddits": {
                "m/tech": ["r/programming", "r/technology", "r/python"],
                "m/news": ["r/news", "r/worldnews"],
                "m/gaming": ["r/gaming", "r/pcmasterrace"],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(multi_config, f)
            temp_path = f.name

        try:
            settings = Settings(temp_path)

            expected_multis = {
                "m/tech": ["r/programming", "r/technology", "r/python"],
                "m/news": ["r/news", "r/worldnews"],
                "m/gaming": ["r/gaming", "r/pcmasterrace"],
            }
            self.assertEqual(settings.multi_reddits, expected_multis)
        finally:
            os.unlink(temp_path)

    def test_settings_handle_missing_file(self):
        """Missing settings file should be handled gracefully."""
        with self.assertRaises(SystemExit):
            Settings("/nonexistent/path/settings.json")

    def test_settings_handle_invalid_json(self):
        """Invalid JSON should be handled gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            temp_path = f.name

        try:
            with self.assertRaises(SystemExit):
                Settings(temp_path)
        finally:
            os.unlink(temp_path)

    def test_environment_variable_integration(self):
        """Settings should integrate with environment variables."""
        # This test depends on the actual implementation details
        # but focuses on the behavior that env vars can override file settings
        config = {"version": "1.0.0", "auth": {"login_on_startup": False}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            # Set environment variables
            os.environ["REDDIT_CLIENT_ID"] = "env_client_id"
            os.environ["REDDIT_CLIENT_SECRET"] = "env_secret"

            settings = Settings(temp_path)

            # Verify environment variables are used
            self.assertEqual(settings.client_id, "env_client_id")
            self.assertEqual(settings.client_secret, "env_secret")

        finally:
            os.unlink(temp_path)
            # Clean up environment
            if "REDDIT_CLIENT_ID" in os.environ:
                del os.environ["REDDIT_CLIENT_ID"]
            if "REDDIT_CLIENT_SECRET" in os.environ:
                del os.environ["REDDIT_CLIENT_SECRET"]


class TestSettingsIntegration(unittest.TestCase):
    """Integration tests for settings in realistic usage scenarios."""

    def test_complete_configuration_workflow(self):
        """Test a complete, realistic configuration."""
        realistic_config = {
            "version": "1.0.0",
            "file_format": "md",
            "update_check_on_startup": False,
            "show_upvotes": True,
            "show_timestamp": True,
            "enable_media_downloads": True,
            "auth": {
                "login_on_startup": True,
                "client_id": "reddit_app_id",
                "client_secret": "reddit_app_secret",
                "username": "my_reddit_user",
                "password": "my_reddit_pass",
            },
            "filters": {
                "keywords": ["spam", "phishing", "malware"],
                "min_upvotes": 5,
                "authors": ["known_troll", "spam_account"],
                "regexes": [r"\b[A-Z]{5,}\b"],  # All caps words
            },
            "filtered_message": "⚠️ Content filtered",
            "default_save_location": "~/Downloads/Reddit",
            "multi_reddits": {
                "m/programming": ["r/programming", "r/python", "r/javascript"],
                "m/science": ["r/science", "r/physics", "r/biology"],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(realistic_config, f)
            temp_path = f.name

        try:
            # Set environment variables for auth credentials (they override JSON)
            os.environ["REDDIT_CLIENT_ID"] = "env_reddit_id"
            os.environ["REDDIT_CLIENT_SECRET"] = "env_reddit_secret"
            os.environ["REDDIT_USERNAME"] = "env_reddit_user"
            os.environ["REDDIT_PASSWORD"] = "env_reddit_pass"

            settings = Settings(temp_path)

            # Verify all major setting categories work together
            self.assertEqual(settings.file_format, "md")
            self.assertEqual(settings.show_upvotes, True)

            # Auth credentials come from environment variables, not JSON
            self.assertEqual(settings.client_id, "env_reddit_id")
            self.assertEqual(settings.client_secret, "env_reddit_secret")
            self.assertEqual(settings.username, "env_reddit_user")
            self.assertEqual(settings.password, "env_reddit_pass")

            # Other settings come from JSON
            self.assertEqual(
                settings.filtered_keywords, ["spam", "phishing", "malware"]
            )
            self.assertEqual(settings.filtered_message, "⚠️ Content filtered")
            self.assertEqual(settings.default_save_location, "~/Downloads/Reddit")
            self.assertIn("m/programming", settings.multi_reddits)
            self.assertEqual(len(settings.multi_reddits["m/programming"]), 3)

            # Clean up environment variables
            for var in [
                "REDDIT_CLIENT_ID",
                "REDDIT_CLIENT_SECRET",
                "REDDIT_USERNAME",
                "REDDIT_PASSWORD",
            ]:
                if var in os.environ:
                    del os.environ[var]

        finally:
            os.unlink(temp_path)

    def test_unicode_and_special_characters(self):
        """Settings should handle unicode and special characters."""
        unicode_config = {
            "version": "1.0.0",
            "filtered_message": "🚫 محتوى مفلتر",  # Arabic text with emoji
            "filters": {
                "keywords": ["スパム", "广告", "रेक्लाम"],  # Japanese, Chinese, Hindi
                "authors": ["用户123", "ユーザー456"],
            },
            "default_save_location": "~/デスクトップ/Reddit",  # Japanese desktop
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(unicode_config, f, ensure_ascii=False)
            temp_path = f.name

        try:
            settings = Settings(temp_path)

            self.assertEqual(settings.filtered_message, "🚫 محتوى مفلتر")
            self.assertIn("スパム", settings.filtered_keywords)
            self.assertIn("广告", settings.filtered_keywords)
            self.assertEqual(settings.default_save_location, "~/デスクトップ/Reddit")

        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
