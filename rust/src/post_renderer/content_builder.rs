use anyhow::Result;
use log::debug;
use serde_json::Value;

use super::formatting::{escape_selftext, format_timestamp, format_upvotes};
use super::media_handler::MediaHandler;
use super::reply_processor::ReplyProcessor;
use crate::settings::Settings;

pub struct PostContentBuilder {
    media_handler: MediaHandler,
    reply_processor: ReplyProcessor,
}

impl PostContentBuilder {
    pub fn new() -> Self {
        Self {
            media_handler: MediaHandler,
            reply_processor: ReplyProcessor::new(),
        }
    }

    pub fn build_post_content(
        &mut self,
        post_data: &Value,
        replies_data: &[Value],
        settings: &Settings,
        colors: &[&str],
        _url: &str,
        target_path: &str,
    ) -> Result<String> {
        let post_info = self.extract_post_info(post_data);
        debug!("Building content for post: '{}'", post_info.title);

        let mut lines = Vec::with_capacity(100);

        self.build_post_header(&post_info, settings, &mut lines);
        self.build_post_content_body(&post_info, settings, &mut lines);
        self.build_lock_message(&post_info, settings, &mut lines);

        if settings.enable_media_downloads {
            self.media_handler
                .process_media(post_data, target_path, &mut lines)?;
        }

        self.reply_processor.process_replies(
            replies_data,
            settings,
            colors,
            &post_info.author,
            &mut lines,
        );

        lines.push("\n".to_string());
        Ok(lines.join(""))
    }

    fn extract_post_info(&self, post_data: &Value) -> PostInfo {
        let title = post_data["title"].as_str().unwrap_or("Untitled");
        let author = post_data["author"].as_str().unwrap_or("[unknown]");
        let subreddit = post_data["subreddit_name_prefixed"].as_str().unwrap_or("");
        let upvotes = post_data["ups"].as_i64().unwrap_or(0) as i32;
        let locked = post_data["locked"].as_bool().unwrap_or(false);
        let selftext = post_data["selftext"].as_str().unwrap_or("");
        let url = post_data["url"].as_str().unwrap_or("");
        let created_utc = post_data["created_utc"].as_f64();

        let timestamp = self.extract_post_timestamp(created_utc);

        PostInfo {
            title: title.to_string(),
            author: author.to_string(),
            subreddit: subreddit.to_string(),
            upvotes,
            locked,
            selftext: selftext.to_string(),
            url: url.to_string(),
            timestamp,
        }
    }

    fn extract_post_timestamp(&self, created_utc: Option<f64>) -> String {
        if let Some(timestamp) = created_utc {
            if let Some(dt) = chrono::DateTime::from_timestamp(timestamp as i64, 0) {
                dt.format("%Y-%m-%d %H:%M:%S").to_string()
            } else {
                String::new()
            }
        } else {
            String::new()
        }
    }

    fn build_post_header(
        &self,
        post_info: &PostInfo,
        settings: &Settings,
        lines: &mut Vec<String>,
    ) {
        let upvotes_display = format_upvotes(post_info.upvotes, settings.show_upvotes);
        let timestamp_display = format_timestamp(&post_info.timestamp, settings.show_timestamp);

        lines.push(format!(
            "**{}** | Posted by u/{} {} {}\n",
            post_info.subreddit, post_info.author, upvotes_display, timestamp_display
        ));
        lines.push(format!("## {}\n", post_info.title));
        lines.push(format!(
            "Original post: [{}]({})\n",
            post_info.url, post_info.url
        ));
    }

    fn build_post_content_body(
        &self,
        post_info: &PostInfo,
        _settings: &Settings,
        lines: &mut Vec<String>,
    ) {
        if !post_info.selftext.is_empty() {
            let selftext_escaped = escape_selftext(&post_info.selftext);
            lines.push(format!("> {}\n", selftext_escaped.replace('\n', "\n> ")));
        }
    }

    fn build_lock_message(
        &self,
        post_info: &PostInfo,
        _settings: &Settings,
        lines: &mut Vec<String>,
    ) {
        if post_info.locked {
            let lock_msg = format!(
                "---\n\n>🔒 **This thread has been locked by the moderators of {}**.\n  New comments cannot be posted\n\n",
                post_info.subreddit
            );
            lines.push(lock_msg);
        }
    }
}

pub fn build_post_content(
    post_data: &Value,
    replies_data: &[Value],
    settings: &Settings,
    colors: &[&str],
    url: &str,
    target_path: &str,
) -> Result<String> {
    let mut builder = PostContentBuilder::new();
    builder.build_post_content(post_data, replies_data, settings, colors, url, target_path)
}

struct PostInfo {
    title: String,
    author: String,
    subreddit: String,
    upvotes: i32,
    locked: bool,
    selftext: String,
    url: String,
    timestamp: String,
}
