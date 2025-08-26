pub fn clean_url(url: &str) -> String {
    let trimmed = url.trim();
    match trimmed.find("?utm_source") {
        Some(pos) => trimmed[..pos].to_string(),
        None => trimmed.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clean_url_basic() {
        let with_utm = "https://example.com/test?utm_source=share&utm_medium=web";
        let without_utm = "https://example.com/test";
        assert_eq!(clean_url(with_utm), without_utm);
        assert_eq!(clean_url(without_utm), without_utm);
    }
}
