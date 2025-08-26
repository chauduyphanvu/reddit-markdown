use reddit_markdown::*;
use serde_json::json;
use tempfile::{tempdir, TempDir};

#[cfg(test)]
mod tests {
    use super::*;

    struct TestUrls;
    impl TestUrls {
        const RUST_POST: &'static str = "https://www.reddit.com/r/rust/comments/abc123/test_post/";
        const PROGRAMMING_POST: &'static str =
            "https://www.reddit.com/r/programming/comments/xyz789/another_test";
        const WITH_UTM: &'static str =
            "https://www.reddit.com/r/rust/comments/abc123/test?utm_source=share&utm_medium=web";
        const WITHOUT_UTM: &'static str = "https://www.reddit.com/r/rust/comments/abc123/test";
        const INVALID_EXAMPLE: &'static str = "https://example.com";
        const INVALID_NOT_URL: &'static str = "not_a_url";
        const INVALID_SUBREDDIT: &'static str = "https://www.reddit.com/r/rust";
        const INVALID_USER: &'static str = "https://www.reddit.com/user/someone";
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
    }

    fn assert_html_with_content(html: &str) {
        assert_html_structure(html);
        assert!(html.contains("<h1>"));
        assert!(html.contains("<strong>"));
    }

    fn create_test_reply_json() -> serde_json::Value {
        json!({
            "data": {
                "replies": {
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "id": "comment1",
                                    "depth": 1,
                                    "body": "This is a test comment"
                                }
                            }
                        ]
                    }
                }
            }
        })
    }

    fn create_empty_reply_json() -> serde_json::Value {
        json!({
            "data": {
                "replies": {}
            }
        })
    }

    fn create_nested_replies_json() -> serde_json::Value {
        json!({
            "data": {
                "replies": {
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "id": "comment1",
                                    "depth": 1,
                                    "body": "First level comment",
                                    "replies": {
                                        "data": {
                                            "children": [
                                                {
                                                    "data": {
                                                        "id": "comment2",
                                                        "depth": 2,
                                                        "body": "Second level reply"
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        })
    }

    #[test]
    fn test_clean_url() {
        assert_eq!(
            reddit_utils::clean_url(TestUrls::WITH_UTM),
            TestUrls::WITHOUT_UTM
        );
        assert_eq!(
            reddit_utils::clean_url(TestUrls::WITHOUT_UTM),
            TestUrls::WITHOUT_UTM
        );
    }

    #[test]
    fn test_valid_url() {
        // Valid URLs
        assert!(reddit_utils::valid_url(TestUrls::RUST_POST));
        assert!(reddit_utils::valid_url(TestUrls::PROGRAMMING_POST));

        // Invalid URLs
        assert!(!reddit_utils::valid_url(TestUrls::INVALID_EXAMPLE));
        assert!(!reddit_utils::valid_url(TestUrls::INVALID_NOT_URL));
        assert!(!reddit_utils::valid_url(TestUrls::INVALID_SUBREDDIT));
        assert!(!reddit_utils::valid_url(TestUrls::INVALID_USER));
    }

    #[test]
    fn test_markdown_to_html() {
        let html = reddit_utils::markdown_to_html(TestData::MARKDOWN);
        assert_html_with_content(&html);
    }

    #[test]
    fn test_ensure_dir_exists() {
        let temp_dir = setup_temp_dir();
        let test_path = temp_dir.path().join("test_subdir");

        assert!(!test_path.exists());
        reddit_utils::ensure_dir_exists(test_path.to_str().unwrap()).unwrap();
        assert!(test_path.exists());
        assert!(test_path.is_dir());
    }

    #[test]
    fn test_generate_filename() {
        let temp_dir = setup_temp_dir();
        let base_dir = temp_dir.path().to_str().unwrap();

        let filename = reddit_utils::generate_filename(
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
    fn test_generate_filename_with_timestamp_dirs() {
        let temp_dir = setup_temp_dir();
        let base_dir = temp_dir.path().to_str().unwrap();

        let filename = reddit_utils::generate_filename(
            base_dir,
            TestUrls::RUST_POST,
            TestData::SUBREDDIT,
            true,
            TestData::TIMESTAMP,
            "md",
            false,
        )
        .unwrap();

        assert!(filename.contains("2023-01-01"));
        assert!(filename.contains("rust"));
        assert!(filename.ends_with("test_post.md"));
    }

    #[test]
    fn test_generate_filename_html_format() {
        let temp_dir = setup_temp_dir();
        let base_dir = temp_dir.path().to_str().unwrap();

        let filename = reddit_utils::generate_filename(
            base_dir,
            TestUrls::RUST_POST,
            TestData::SUBREDDIT,
            false,
            TestData::TIMESTAMP,
            "html",
            false,
        )
        .unwrap();

        assert!(filename.ends_with("test_post.html"));
    }

    #[test]
    fn test_get_replies_empty() {
        let empty_reply = create_empty_reply_json();
        let replies = reddit_utils::get_replies(&empty_reply, 5);
        assert_eq!(replies.len(), 0);
    }

    #[test]
    fn test_get_replies_with_data() {
        let reply_data = create_test_reply_json();
        let replies = reddit_utils::get_replies(&reply_data, 5);
        assert_eq!(replies.len(), 1);
        assert!(replies.contains_key("comment1"));
    }

    #[test]
    fn test_get_replies_nested() {
        let reply_data = create_nested_replies_json();
        let replies = reddit_utils::get_replies(&reply_data, 5);
        assert_eq!(replies.len(), 2);
        assert!(replies.contains_key("comment1"));
        assert!(replies.contains_key("comment2"));
    }

    #[test]
    fn test_get_replies_depth_limit() {
        let reply_data = create_nested_replies_json();
        let replies = reddit_utils::get_replies(&reply_data, 1);
        assert_eq!(replies.len(), 1);
        assert!(replies.contains_key("comment1"));
        assert!(!replies.contains_key("comment2"));
    }

    #[test]
    fn test_clean_url_edge_cases() {
        assert_eq!(reddit_utils::clean_url(""), "");
        assert_eq!(reddit_utils::clean_url("   "), "");
        assert_eq!(
            reddit_utils::clean_url("https://example.com?utm_source="),
            "https://example.com"
        );
        // clean_url splits on "?utm_source" so anything after that is removed
        assert_eq!(
            reddit_utils::clean_url("https://example.com?other=param&utm_source=share"),
            "https://example.com?other=param&utm_source=share"
        );
    }

    #[test]
    fn test_valid_url_edge_cases() {
        assert!(!reddit_utils::valid_url(""));
        assert!(!reddit_utils::valid_url("   "));
        assert!(!reddit_utils::valid_url("https://www.reddit.com/r/"));
        assert!(!reddit_utils::valid_url(
            "https://www.reddit.com/r/rust/comments/"
        ));
        assert!(!reddit_utils::valid_url(
            "https://www.reddit.com/r/rust/comments/abc123/"
        ));
        assert!(reddit_utils::valid_url(
            "https://www.reddit.com/r/rust/comments/abc123/test"
        ));
        assert!(reddit_utils::valid_url(
            "https://www.reddit.com/r/r_usttest/comments/abc123/test_post"
        ));
        assert!(reddit_utils::valid_url(
            "https://www.reddit.com/r/123numbers/comments/xyz789/post123"
        ));
    }

    #[test]
    fn test_generate_filename_edge_cases() {
        let temp_dir = setup_temp_dir();
        let base_dir = temp_dir.path().to_str().unwrap();

        // Test with special characters in URL
        let special_url =
            "https://www.reddit.com/r/rust/comments/abc123/test-post_with.special%20chars/";
        let filename = reddit_utils::generate_filename(
            base_dir,
            special_url,
            TestData::SUBREDDIT,
            false,
            TestData::TIMESTAMP,
            "md",
            false,
        )
        .unwrap();
        assert!(filename.contains("test-post_with.special"));

        // Test with very long timestamp directory structure
        let filename_with_dirs = reddit_utils::generate_filename(
            base_dir,
            TestUrls::RUST_POST,
            TestData::SUBREDDIT,
            true,
            TestData::TIMESTAMP,
            "html",
            true,
        )
        .unwrap();
        assert!(filename_with_dirs.contains("2023-01-01"));
        assert!(filename_with_dirs.ends_with("test_post.html"));
    }

    #[test]
    fn test_ensure_dir_exists_nested() {
        let temp_dir = setup_temp_dir();
        let nested_path = temp_dir.path().join("level1").join("level2").join("level3");

        assert!(!nested_path.exists());
        reddit_utils::ensure_dir_exists(nested_path.to_str().unwrap()).unwrap();
        assert!(nested_path.exists());
        assert!(nested_path.is_dir());
    }

    #[test]
    fn test_ensure_dir_exists_existing_dir() {
        let temp_dir = setup_temp_dir();
        let existing_path = temp_dir.path();

        // Should succeed on existing directory
        reddit_utils::ensure_dir_exists(existing_path.to_str().unwrap()).unwrap();
        assert!(existing_path.exists());
        assert!(existing_path.is_dir());
    }

    #[test]
    fn test_markdown_to_html_edge_cases() {
        // Empty markdown
        let html = reddit_utils::markdown_to_html("");
        assert_html_structure(&html);

        // Only whitespace
        let html = reddit_utils::markdown_to_html("   \n  \t  ");
        assert_html_structure(&html);

        // Complex markdown with links and code
        let complex_md =
            "# Header\n\n[Link](https://example.com)\n\n```rust\nfn test() {}\n```\n\n> Quote";
        let html = reddit_utils::markdown_to_html(complex_md);
        assert_html_structure(&html);
        assert!(html.contains("<h1"));
        assert!(html.contains("<a"));
        assert!(html.contains("<code"));
        assert!(html.contains("<blockquote"));
    }
}
