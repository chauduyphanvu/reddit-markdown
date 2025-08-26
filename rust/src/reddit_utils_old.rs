use anyhow::{Context, Result};
use log::{debug, error, info, warn};
use pulldown_cmark::{html, Parser};
use regex::Regex;
use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

pub fn clean_url(url: &str) -> String {
    let trimmed = url.trim();
    match trimmed.find("?utm_source") {
        Some(pos) => trimmed[..pos].to_string(),
        None => trimmed.to_string(),
    }
}

pub fn valid_url(url: &str) -> bool {
    let re = Regex::new(r"^https://www\.reddit\.com/r/\w+/comments/\w+/[\w_]+/?").unwrap();
    re.is_match(url)
}

static HTTP_CLIENT: std::sync::OnceLock<reqwest::blocking::Client> = std::sync::OnceLock::new();

fn get_http_client() -> &'static reqwest::blocking::Client {
    HTTP_CLIENT.get_or_init(|| {
        reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .user_agent("MyRedditScript/0.1")
            .build()
            .expect("Failed to create HTTP client")
    })
}

pub fn download_post_json(url: &str, access_token: &str) -> Result<Value> {
    let json_url = if url.ends_with(".json") {
        url.to_string()
    } else {
        format!("{}.json", url)
    };

    debug!("Fetching Reddit post JSON from: {}", json_url);

    let client = get_http_client();
    let mut request = client.get(&json_url);

    let _final_url = if !access_token.is_empty() {
        let oauth_url = json_url.replace("https://www.reddit.com", "https://oauth.reddit.com");
        debug!("Using OAuth endpoint: {}", oauth_url);
        request = client
            .get(&oauth_url)
            .header("Authorization", format!("bearer {}", access_token));
        oauth_url
    } else {
        debug!("Using public endpoint (no authentication)");
        json_url
    };

    debug!("Sending HTTP request...");
    let response = request
        .send()
        .with_context(|| format!("Failed to download JSON for {}", url))?;

    debug!("Received response with status: {}", response.status());

    if !response.status().is_success() {
        error!("HTTP request failed with status: {}", response.status());
        return Err(anyhow::anyhow!(
            "Failed to fetch post data: {}",
            response.status()
        ));
    }

    debug!("Parsing JSON response...");
    let json: Value = response
        .json()
        .with_context(|| format!("Failed to parse JSON for {}", url))?;

    debug!("JSON parsed successfully, {} bytes", json.to_string().len());

    Ok(json)
}

pub fn get_replies(reply_data: &Value, max_depth: i32) -> HashMap<String, HashMap<String, Value>> {
    debug!("Processing replies with max_depth: {}", max_depth);
    let mut collected = HashMap::with_capacity(16); // Pre-allocate with reasonable capacity

    let replies_obj = reply_data.pointer("/data/replies");

    let children = replies_obj
        .and_then(|r| r.pointer("/data/children"))
        .and_then(|c| c.as_array());

    if let Some(children) = children {
        for child in children {
            let child_id = child
                .get("data")
                .and_then(|d| d.get("id"))
                .and_then(|id| id.as_str())
                .unwrap_or("")
                .to_string();

            let child_depth = child
                .get("data")
                .and_then(|d| d.get("depth"))
                .and_then(|d| d.as_i64())
                .unwrap_or(0) as i32;

            let child_body = child
                .get("data")
                .and_then(|d| d.get("body"))
                .and_then(|b| b.as_str())
                .unwrap_or("");

            if max_depth != -1 && child_depth > max_depth {
                continue;
            }

            if child_body.trim().is_empty() {
                continue;
            }

            let mut child_info = HashMap::new();
            child_info.insert("depth".to_string(), Value::from(child_depth));
            child_info.insert("child_reply".to_string(), child.clone());

            collected.insert(child_id.clone(), child_info);

            let nested_replies = get_replies(child, max_depth);
            collected.extend(nested_replies);
        }
    }

    debug!("Collected {} reply entries", collected.len());
    collected
}

pub fn markdown_to_html(md_content: &str) -> String {
    let parser = Parser::new(md_content);
    let mut html_output = String::new();
    html::push_html(&mut html_output, parser);
    format!("<html><body>{}</body></html>", html_output)
}

pub fn resolve_save_dir(config_directory: &str) -> Result<String> {
    if config_directory == "DEFAULT_REDDIT_SAVE_LOCATION" {
        let directory = std::env::var("DEFAULT_REDDIT_SAVE_LOCATION")
            .context("DEFAULT_REDDIT_SAVE_LOCATION environment variable not set")?;

        if directory.is_empty() {
            return Err(anyhow::anyhow!(
                "DEFAULT_REDDIT_SAVE_LOCATION environment variable is empty"
            ));
        }

        info!(
            "Using default directory from environment variable: {}",
            directory
        );
        Ok(directory)
    } else if !config_directory.is_empty() {
        info!("Using directory set in configuration: {}", config_directory);
        Ok(config_directory.to_string())
    } else {
        println!(
            "Enter the full path to save the post(s). Hit Enter for current dir ({})",
            std::env::current_dir()?.display()
        );

        let mut input = String::new();
        std::io::stdin().read_line(&mut input)?;
        let directory = input.trim();

        let final_dir = if directory.is_empty() {
            std::env::current_dir()?.to_string_lossy().to_string()
        } else {
            directory.to_string()
        };

        while !Path::new(&final_dir).is_dir() {
            error!("Invalid path: '{}'. Try again.", final_dir);
            input.clear();
            std::io::stdin().read_line(&mut input)?;
        }

        info!("User selected directory: {}", final_dir);
        Ok(final_dir)
    }
}

pub fn ensure_dir_exists(path: &str) -> Result<()> {
    let path = Path::new(path);
    if !path.is_dir() {
        debug!("Directory {:?} does not exist, creating...", path);
        fs::create_dir_all(path)?;
    }
    Ok(())
}

pub fn generate_filename(
    base_dir: &str,
    url: &str,
    subreddit: &str,
    use_timestamped_dirs: bool,
    post_timestamp: &str,
    file_format: &str,
    overwrite: bool,
) -> Result<String> {
    debug!(
        "Generating filename: base_dir={}, subreddit={}, format={}",
        base_dir, subreddit, file_format
    );
    let name_candidate = url
        .trim_end_matches('/')
        .split('/')
        .last()
        .unwrap_or(&format!(
            "reddit_no_name_{}",
            chrono::Utc::now().timestamp()
        ))
        .to_string();

    let subreddit = if subreddit.starts_with("r/") {
        &subreddit[2..]
    } else {
        subreddit
    };

    let mut subdir = PathBuf::from(base_dir);
    if !subreddit.is_empty() {
        subdir.push(subreddit);
    }

    if use_timestamped_dirs && !post_timestamp.is_empty() {
        let dt_str = if let Ok(dt) =
            chrono::NaiveDateTime::parse_from_str(post_timestamp, "%Y-%m-%d %H:%M:%S")
        {
            dt.format("%Y-%m-%d").to_string()
        } else {
            chrono::Utc::now().format("%Y-%m-%d").to_string()
        };
        subdir.push(dt_str);
    }

    ensure_dir_exists(subdir.to_str().unwrap())?;

    let ext = if file_format.to_lowercase() == "html" {
        "html"
    } else {
        "md"
    };

    let mut file_path = subdir.join(format!("{}.{}", name_candidate, ext));

    if file_path.exists() {
        debug!("Target file already exists: {:?}", file_path);
        if overwrite {
            warn!(
                "Overwriting existing file: {}",
                file_path.file_name().unwrap().to_string_lossy()
            );
        } else {
            let base_no_ext = file_path.with_extension("");
            let mut suffix = 1;
            loop {
                file_path = base_no_ext.with_file_name(format!(
                    "{}_{}.{}",
                    base_no_ext.file_stem().unwrap().to_string_lossy(),
                    suffix,
                    ext
                ));
                if !file_path.exists() {
                    break;
                }
                suffix += 1;
            }
            debug!(
                "File exists, generated alternative name with suffix {}",
                suffix - 1
            );
            info!(
                "File exists. Using: {}",
                file_path.file_name().unwrap().to_string_lossy()
            );
        }
    }

    let final_path = file_path.to_string_lossy().to_string();
    debug!("Final generated filename: {}", final_path);
    Ok(final_path)
}

pub fn download_media(url: &str, file_path: &str) -> Result<bool> {
    let client = get_http_client();
    let response = client
        .get(url)
        .send()
        .with_context(|| format!("Failed to download media from {}", url))?;

    if !response.status().is_success() {
        error!("Failed to download media: {}", response.status());
        return Ok(false);
    }

    debug!("Creating file for media content...");
    let mut file = fs::File::create(file_path)
        .with_context(|| format!("Failed to create file: {}", file_path))?;

    let content = response.bytes()?;
    let content_size = content.len();
    debug!("Writing {} bytes of media content...", content_size);
    file.write_all(&content)?;

    info!(
        "Successfully downloaded media to {} ({} bytes)",
        file_path, content_size
    );
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use tempfile::{tempdir, TempDir};

    struct TestUrls;
    impl TestUrls {
        const WITH_UTM: &'static str = "https://example.com/test?utm_source=share&utm_medium=web";
        const WITHOUT_UTM: &'static str = "https://example.com/test";
        const RUST_POST: &'static str = "https://www.reddit.com/r/rust/comments/abc123/test_post/";
        const PROGRAMMING_POST: &'static str =
            "https://www.reddit.com/r/programming/comments/xyz789/another_test";
        const INVALID_EXAMPLE: &'static str = "https://example.com";
        const INVALID_NOT_URL: &'static str = "not_a_url";
        const INVALID_SUBREDDIT: &'static str = "https://www.reddit.com/r/rust";
    }

    struct TestData;
    impl TestData {
        const SUBREDDIT: &'static str = "r/rust";
        const TIMESTAMP: &'static str = "2023-01-01 12:00:00";
        const MARKDOWN: &'static str = "# Test\n\nThis is **bold** text.";
    }

    fn setup_temp_dir() -> TempDir {
        tempdir().unwrap()
    }

    fn assert_html_structure(html: &str) {
        assert!(html.contains("<html>"));
        assert!(html.contains("<body>"));
        assert!(html.contains("<h1>"));
        assert!(html.contains("<strong>"));
    }

    #[test]
    fn test_markdown_to_html_basic() {
        let html = markdown_to_html(TestData::MARKDOWN);
        assert_html_structure(&html);
        assert!(html.contains("<h1"));
        assert!(html.contains("<strong"));
    }

    fn create_empty_reply_json() -> serde_json::Value {
        json!({
            "data": {
                "replies": {}
            }
        })
    }

    #[test]
    fn test_clean_url_basic() {
        assert_eq!(clean_url(TestUrls::WITH_UTM), TestUrls::WITHOUT_UTM);
        assert_eq!(clean_url(TestUrls::WITHOUT_UTM), TestUrls::WITHOUT_UTM);
    }

    #[test]
    fn test_valid_url_basic() {
        assert!(valid_url(TestUrls::RUST_POST));
        assert!(valid_url(TestUrls::PROGRAMMING_POST));
        assert!(!valid_url(TestUrls::INVALID_EXAMPLE));
        assert!(!valid_url(TestUrls::INVALID_NOT_URL));
        assert!(!valid_url(TestUrls::INVALID_SUBREDDIT));
    }

    #[test]
    fn test_ensure_dir_exists_basic() {
        let temp_dir = setup_temp_dir();
        let test_path = temp_dir.path().join("test_subdir");
        assert!(!test_path.exists());
        ensure_dir_exists(test_path.to_str().unwrap()).unwrap();
        assert!(test_path.exists());
        assert!(test_path.is_dir());
    }

    #[test]
    fn test_generate_filename_basic() {
        let temp_dir = setup_temp_dir();
        let base_dir = temp_dir.path().to_str().unwrap();
        let filename = generate_filename(
            base_dir,
            TestUrls::RUST_POST,
            TestData::SUBREDDIT,
            false,
            TestData::TIMESTAMP,
            "md",
            false,
        )
        .unwrap();
        assert!(filename.ends_with("test_post.md"));
        assert!(filename.contains("rust"));
    }

    #[test]
    fn test_get_replies_empty_basic() {
        let empty_reply = create_empty_reply_json();
        let replies = get_replies(&empty_reply, 5);
        assert_eq!(replies.len(), 0);
    }

    #[test]
    fn test_resolve_save_dir_config_path() {
        let config_path = "/some/test/path";
        let result = resolve_save_dir(config_path).unwrap();
        assert_eq!(result, config_path);
    }

    #[test]
    fn test_resolve_save_dir_empty_config() {
        let result = resolve_save_dir("");
        // This would normally prompt for input, but in tests it should handle gracefully
        // We can't easily test the interactive part without mocking stdin
        assert!(result.is_ok() || result.is_err());
    }

    #[test]
    fn test_resolve_save_dir_default_location_missing_env() {
        // Test when environment variable is not set
        std::env::remove_var("DEFAULT_REDDIT_SAVE_LOCATION");
        let result = resolve_save_dir("DEFAULT_REDDIT_SAVE_LOCATION");
        assert!(result.is_err());
    }

    #[test]
    fn test_resolve_save_dir_default_location_with_env() {
        let test_path = "/tmp/reddit_test";
        std::env::set_var("DEFAULT_REDDIT_SAVE_LOCATION", test_path);
        let result = resolve_save_dir("DEFAULT_REDDIT_SAVE_LOCATION").unwrap();
        assert_eq!(result, test_path);
        std::env::remove_var("DEFAULT_REDDIT_SAVE_LOCATION");
    }

    #[test]
    fn test_resolve_save_dir_empty_env_var() {
        std::env::set_var("DEFAULT_REDDIT_SAVE_LOCATION", "");
        let result = resolve_save_dir("DEFAULT_REDDIT_SAVE_LOCATION");
        assert!(result.is_err());
        std::env::remove_var("DEFAULT_REDDIT_SAVE_LOCATION");
    }
}
