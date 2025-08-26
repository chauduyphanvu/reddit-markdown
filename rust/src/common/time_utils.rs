use chrono::DateTime;

/// Convert Unix timestamp to formatted date string
pub fn format_timestamp(timestamp: f64) -> String {
    if let Some(dt) = DateTime::from_timestamp(timestamp as i64, 0) {
        dt.format("%Y-%m-%d %H:%M:%S").to_string()
    } else {
        String::new()
    }
}

/// Get current timestamp as formatted string
pub fn current_timestamp() -> String {
    chrono::Utc::now().format("%Y-%m-%d %H:%M:%S").to_string()
}

/// Convert timestamp to date-only string for directory names
pub fn timestamp_to_date(timestamp: &str) -> String {
    if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(timestamp, "%Y-%m-%d %H:%M:%S") {
        dt.format("%Y-%m-%d").to_string()
    } else {
        chrono::Utc::now().format("%Y-%m-%d").to_string()
    }
}
