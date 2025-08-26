use anyhow::{Context, Result};
use log::{debug, error, info, warn};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

fn default_true() -> bool {
    true
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct AuthSettings {
    pub login_on_startup: bool,
    pub client_id: String,
    pub client_secret: String,
    pub username: String,
    pub password: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Filters {
    pub keywords: Vec<String>,
    pub min_upvotes: i32,
    pub authors: Vec<String>,
    pub regexes: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Settings {
    pub version: String,
    pub file_format: String,
    pub update_check_on_startup: bool,
    pub auth: AuthSettings,
    pub show_upvotes: bool,
    pub reply_depth_max: i32,
    pub reply_depth_color_indicators: bool,
    pub line_break_between_parent_replies: bool,
    pub show_auto_mod_comment: bool,
    pub overwrite_existing_file: bool,
    pub save_posts_by_subreddits: bool,
    pub show_timestamp: bool,
    pub filtered_message: String,
    pub filters: Filters,
    pub default_save_location: String,
    pub use_timestamped_directories: bool,
    #[serde(default = "default_true")]
    pub enable_media_downloads: bool,
    pub multi_reddits: HashMap<String, Vec<String>>,
}

impl Settings {
    pub fn load(settings_file: &str) -> Result<Self> {
        let path = Path::new(settings_file);
        if !path.exists() {
            return Err(anyhow::anyhow!(
                "settings.json not found at '{}'. Exiting...",
                settings_file
            ));
        }

        let contents = fs::read_to_string(path)
            .with_context(|| format!("Failed to read settings file: {}", settings_file))?;

        let settings: Settings = serde_json::from_str(&contents)
            .with_context(|| format!("Failed to parse settings file: {}", settings_file))?;

        info!("Settings loaded from '{}'.", settings_file);
        Ok(settings)
    }

    pub fn check_for_updates(&self) -> Result<()> {
        let check_url = "https://api.github.com/repos/chauduyphanvu/reddit-markdown/releases";
        debug!("Checking for updates at {}", check_url);

        let client = reqwest::blocking::Client::new();
        let resp = client
            .get(check_url)
            .header("User-Agent", "Mozilla/5.0")
            .timeout(std::time::Duration::from_secs(5))
            .send();

        match resp {
            Ok(response) => {
                if response.status().is_success() {
                    let releases: Vec<serde_json::Value> = response.json()?;
                    if !releases.is_empty() {
                        let latest_tag = releases[0]["tag_name"]
                            .as_str()
                            .unwrap_or("0.0.0")
                            .to_string();

                        if self.is_newer_version(&latest_tag) {
                            info!(
                                "A new version ({}) is available. You have {}. \
                                Download it from https://github.com/chauduyphanvu/reddit-markdown.",
                                latest_tag, self.version
                            );
                        } else {
                            debug!("Current version {} is up-to-date.", self.version);
                        }
                    } else {
                        warn!("Could not fetch release info from GitHub. Please check manually.");
                    }
                }
            }
            Err(e) => {
                error!("Could not check for updates: {}", e);
            }
        }
        Ok(())
    }

    fn is_newer_version(&self, latest: &str) -> bool {
        let current_parts: Vec<u32> = self
            .version
            .split('.')
            .filter_map(|s| s.parse().ok())
            .collect();
        let latest_parts: Vec<u32> = latest.split('.').filter_map(|s| s.parse().ok()).collect();

        for i in 0..3 {
            let current = current_parts.get(i).unwrap_or(&0);
            let latest = latest_parts.get(i).unwrap_or(&0);
            if latest > current {
                return true;
            } else if latest < current {
                return false;
            }
        }
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_settings_load_valid() {
        let json_content = r#"{
            "version": "1.0.0",
            "file_format": "md",
            "update_check_on_startup": false,
            "auth": {
                "login_on_startup": false,
                "client_id": "test_id",
                "client_secret": "test_secret",
                "username": "test_user",
                "password": "test_pass"
            },
            "show_upvotes": true,
            "reply_depth_max": 5,
            "reply_depth_color_indicators": true,
            "line_break_between_parent_replies": true,
            "show_auto_mod_comment": false,
            "overwrite_existing_file": false,
            "save_posts_by_subreddits": true,
            "show_timestamp": true,
            "filtered_message": "filtered",
            "filters": {
                "keywords": [],
                "min_upvotes": 0,
                "authors": [],
                "regexes": []
            },
            "default_save_location": "/tmp",
            "use_timestamped_directories": false,
            "enable_media_downloads": true,
            "multi_reddits": {}
        }"#;

        let mut temp_file = NamedTempFile::new().unwrap();
        temp_file.write_all(json_content.as_bytes()).unwrap();
        let temp_path = temp_file.path().to_str().unwrap();

        let settings = Settings::load(temp_path).unwrap();
        assert_eq!(settings.version, "1.0.0");
        assert_eq!(settings.file_format, "md");
        assert_eq!(settings.auth.client_id, "test_id");
        assert!(settings.show_upvotes);
        assert_eq!(settings.reply_depth_max, 5);
    }

    #[test]
    fn test_settings_load_missing_file() {
        let result = Settings::load("nonexistent_file.json");
        assert!(result.is_err());
    }

    #[test]
    fn test_is_newer_version() {
        let settings = Settings {
            version: "1.0.0".to_string(),
            file_format: "md".to_string(),
            update_check_on_startup: false,
            auth: AuthSettings {
                login_on_startup: false,
                client_id: "test".to_string(),
                client_secret: "test".to_string(),
                username: "test".to_string(),
                password: "test".to_string(),
            },
            show_upvotes: true,
            reply_depth_max: 5,
            reply_depth_color_indicators: true,
            line_break_between_parent_replies: true,
            show_auto_mod_comment: false,
            overwrite_existing_file: false,
            save_posts_by_subreddits: true,
            show_timestamp: true,
            filtered_message: "filtered".to_string(),
            filters: Filters {
                keywords: vec![],
                min_upvotes: 0,
                authors: vec![],
                regexes: vec![],
            },
            default_save_location: "/tmp".to_string(),
            use_timestamped_directories: false,
            enable_media_downloads: true,
            multi_reddits: std::collections::HashMap::new(),
        };

        assert!(settings.is_newer_version("1.0.1"));
        assert!(settings.is_newer_version("1.1.0"));
        assert!(settings.is_newer_version("2.0.0"));

        assert!(!settings.is_newer_version("1.0.0"));
        assert!(!settings.is_newer_version("0.9.9"));
    }
}
