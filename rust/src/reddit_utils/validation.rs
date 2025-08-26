use regex::Regex;

pub fn valid_url(url: &str) -> bool {
    let re = Regex::new(r"^https://www\.reddit\.com/r/\w+/comments/\w+/[\w_]+/?").unwrap();
    re.is_match(url)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_url_basic() {
        let rust_post = "https://www.reddit.com/r/rust/comments/abc123/test_post/";
        let programming_post = "https://www.reddit.com/r/programming/comments/xyz789/another_test";
        let invalid_example = "https://example.com";
        let invalid_not_url = "not_a_url";
        let invalid_subreddit = "https://www.reddit.com/r/rust";

        assert!(valid_url(rust_post));
        assert!(valid_url(programming_post));
        assert!(!valid_url(invalid_example));
        assert!(!valid_url(invalid_not_url));
        assert!(!valid_url(invalid_subreddit));
    }
}
