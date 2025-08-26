use log::debug;
use regex::Regex;

pub fn apply_filter(
    author: &str,
    text: &str,
    upvotes: i32,
    filtered_keywords: &[String],
    filtered_authors: &[String],
    min_upvotes: i32,
    filtered_regexes: &[String],
    filtered_message: &str,
) -> String {
    for kw in filtered_keywords {
        if text.to_lowercase().contains(&kw.to_lowercase()) {
            debug!("Comment filtered due to keyword '{}'.", kw);
            return filtered_message.to_string();
        }
    }

    if filtered_authors.contains(&author.to_string()) {
        debug!(
            "Comment filtered because author '{}' is in filtered_authors.",
            author
        );
        return filtered_message.to_string();
    }

    if upvotes < min_upvotes {
        debug!(
            "Comment filtered because upvotes ({}) is less than min_upvotes ({}).",
            upvotes, min_upvotes
        );
        return filtered_message.to_string();
    }

    for rgx in filtered_regexes {
        if let Ok(pattern) = Regex::new(rgx) {
            if pattern.is_match(text) {
                debug!("Comment filtered due to regex '{}'.", rgx);
                return filtered_message.to_string();
            }
        }
    }

    text.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_apply_filter_no_filters() {
        let result = apply_filter(
            "testuser",
            "This is a normal comment",
            10,
            &[],
            &[],
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "This is a normal comment");
    }

    #[test]
    fn test_apply_filter_keyword() {
        let keywords = vec!["spam".to_string()];
        let result = apply_filter(
            "testuser",
            "This is spam content",
            10,
            &keywords,
            &[],
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");
    }

    #[test]
    fn test_apply_filter_keyword_case_insensitive() {
        let keywords = vec!["SPAM".to_string()];
        let result = apply_filter(
            "testuser",
            "This is spam content",
            10,
            &keywords,
            &[],
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");
    }

    #[test]
    fn test_apply_filter_author() {
        let authors = vec!["baduser".to_string()];
        let result = apply_filter(
            "baduser",
            "This is a normal comment",
            10,
            &[],
            &authors,
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");
    }

    #[test]
    fn test_apply_filter_min_upvotes() {
        let result = apply_filter(
            "testuser",
            "This is a normal comment",
            5,
            &[],
            &[],
            10, // min_upvotes is 10, but comment has only 5
            &[],
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");
    }

    #[test]
    fn test_apply_filter_regex() {
        let regexes = vec![r"\d{3}-\d{3}-\d{4}".to_string()]; // Phone number pattern
        let result = apply_filter(
            "testuser",
            "Call me at 123-456-7890",
            10,
            &[],
            &[],
            0,
            &regexes,
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");
    }

    #[test]
    fn test_apply_filter_regex_no_match() {
        let regexes = vec![r"\d{3}-\d{3}-\d{4}".to_string()];
        let result = apply_filter(
            "testuser",
            "This is a normal comment",
            10,
            &[],
            &[],
            0,
            &regexes,
            "[filtered]",
        );
        assert_eq!(result, "This is a normal comment");
    }

    #[test]
    fn test_apply_filter_invalid_regex() {
        let regexes = vec!["[".to_string()]; // Invalid regex
        let result = apply_filter(
            "testuser",
            "This is a normal comment",
            10,
            &[],
            &[],
            0,
            &regexes,
            "[filtered]",
        );
        // Should pass through since regex is invalid
        assert_eq!(result, "This is a normal comment");
    }

    #[test]
    fn test_apply_filter_multiple_keywords() {
        let keywords = vec![
            "spam".to_string(),
            "scam".to_string(),
            "phishing".to_string(),
        ];

        // Test first keyword match
        let result = apply_filter(
            "user1",
            "This is spam content",
            10,
            &keywords,
            &[],
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");

        // Test second keyword match
        let result = apply_filter(
            "user2",
            "This is a scam attempt",
            10,
            &keywords,
            &[],
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");

        // Test no keyword match
        let result = apply_filter(
            "user3",
            "This is normal content",
            10,
            &keywords,
            &[],
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "This is normal content");
    }

    #[test]
    fn test_apply_filter_multiple_authors() {
        let authors = vec![
            "baduser1".to_string(),
            "baduser2".to_string(),
            "spammer".to_string(),
        ];

        // Test filtered author
        let result = apply_filter(
            "baduser1",
            "Normal comment",
            10,
            &[],
            &authors,
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");

        // Test non-filtered author
        let result = apply_filter(
            "gooduser",
            "Normal comment",
            10,
            &[],
            &authors,
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "Normal comment");
    }

    #[test]
    fn test_apply_filter_combined_filters() {
        let keywords = vec!["test".to_string()];
        let authors = vec!["baduser".to_string()];
        let regexes = vec![r"http://".to_string()];

        // Should be filtered by keyword
        let result = apply_filter(
            "gooduser",
            "This is a test comment",
            10,
            &keywords,
            &[],
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");

        // Should be filtered by author
        let result = apply_filter(
            "baduser",
            "Normal comment",
            10,
            &[],
            &authors,
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");

        // Should be filtered by regex
        let result = apply_filter(
            "gooduser",
            "Check http://example.com",
            10,
            &[],
            &[],
            0,
            &regexes,
            "[filtered]",
        );
        assert_eq!(result, "[filtered]");

        // Should pass all filters
        let result = apply_filter(
            "gooduser",
            "Normal comment",
            10,
            &keywords,
            &authors,
            0,
            &regexes,
            "[filtered]",
        );
        assert_eq!(result, "Normal comment");
    }

    #[test]
    fn test_apply_filter_edge_case_upvotes() {
        // Test exact match for minimum upvotes
        let result = apply_filter("user", "comment", 10, &[], &[], 10, &[], "[filtered]");
        assert_eq!(result, "comment");

        // Test just below minimum
        let result = apply_filter("user", "comment", 9, &[], &[], 10, &[], "[filtered]");
        assert_eq!(result, "[filtered]");

        // Test negative upvotes
        let result = apply_filter("user", "comment", -5, &[], &[], 0, &[], "[filtered]");
        assert_eq!(result, "[filtered]");
    }

    #[test]
    fn test_apply_filter_empty_inputs() {
        // Test with empty comment
        let result = apply_filter("user", "", 10, &[], &[], 0, &[], "[filtered]");
        assert_eq!(result, "");

        // Test with empty replacement text
        let result = apply_filter(
            "spam_user",
            "spam content",
            10,
            &["spam".to_string()],
            &[],
            0,
            &[],
            "",
        );
        assert_eq!(result, "");

        // Test with empty username
        let result = apply_filter(
            "",
            "normal comment",
            10,
            &[],
            &["baduser".to_string()],
            0,
            &[],
            "[filtered]",
        );
        assert_eq!(result, "normal comment");
    }
}
