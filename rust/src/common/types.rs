use serde_json::Value;

/// Common result type for Reddit operations
pub type RedditResult<T> = anyhow::Result<T>;

/// Wrapper for post data with commonly accessed fields
#[derive(Debug, Clone)]
pub struct PostData {
    pub raw: Value,
    pub title: String,
    pub author: String,
    pub subreddit: String,
    pub upvotes: i32,
    pub timestamp: String,
    pub url: String,
    pub selftext: String,
    pub locked: bool,
}

impl PostData {
    pub fn from_json(data: &Value) -> Self {
        Self {
            raw: data.clone(),
            title: data["title"].as_str().unwrap_or("Untitled").to_string(),
            author: data["author"].as_str().unwrap_or("[unknown]").to_string(),
            subreddit: data["subreddit_name_prefixed"]
                .as_str()
                .unwrap_or("")
                .to_string(),
            upvotes: data["ups"].as_i64().unwrap_or(0) as i32,
            timestamp: extract_timestamp(&data["created_utc"]),
            url: data["url"].as_str().unwrap_or("").to_string(),
            selftext: data["selftext"].as_str().unwrap_or("").to_string(),
            locked: data["locked"].as_bool().unwrap_or(false),
        }
    }
}

fn extract_timestamp(created_utc: &Value) -> String {
    if let Some(timestamp) = created_utc.as_f64() {
        if let Some(dt) = chrono::DateTime::from_timestamp(timestamp as i64, 0) {
            dt.format("%Y-%m-%d %H:%M:%S").to_string()
        } else {
            String::new()
        }
    } else {
        String::new()
    }
}

/// Processing statistics
#[derive(Debug, Default)]
pub struct ProcessingStats {
    pub successful: usize,
    pub failed: usize,
    pub total: usize,
}

impl ProcessingStats {
    pub fn success_rate(&self) -> f64 {
        if self.total == 0 {
            0.0
        } else {
            self.successful as f64 / self.total as f64 * 100.0
        }
    }
}
