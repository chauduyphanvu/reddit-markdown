/// Color indicators for reply depth visualization
pub const REPLY_DEPTH_COLORS: &[&str] = &["🟩", "🟨", "🟧", "🟦", "🟪", "🟥", "🟫", "⬛️", "⬜️"];

/// Default timeout for HTTP requests in seconds
pub const HTTP_TIMEOUT_SECS: u64 = 10;

/// User agent string for HTTP requests
pub const USER_AGENT: &str = "MyRedditScript/0.1";

/// Base URLs for Reddit API
pub const REDDIT_BASE_URL: &str = "https://www.reddit.com";
pub const REDDIT_OAUTH_URL: &str = "https://oauth.reddit.com";

/// File extensions
pub const MARKDOWN_EXT: &str = "md";
pub const HTML_EXT: &str = "html";

/// Progress bar template
pub const PROGRESS_BAR_TEMPLATE: &str =
    "{spinner:.green} [{elapsed_precise}] [{wide_bar:.cyan/blue}] {pos}/{len} ({eta}) {msg}";

/// Progress bar characters
pub const PROGRESS_BAR_CHARS: &str = "#>-";
