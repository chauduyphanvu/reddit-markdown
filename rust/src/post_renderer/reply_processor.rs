use serde_json::Value;
use std::collections::HashMap;

use super::formatting::{
    format_author_with_op_marker, format_child_comment_body, format_comment_body, format_timestamp,
    format_upvotes,
};
use crate::filters::apply_filter;
use crate::reddit_utils::get_replies;
use crate::settings::Settings;

pub struct ReplyProcessor;

impl ReplyProcessor {
    pub fn new() -> Self {
        Self
    }

    pub fn process_replies(
        &self,
        replies_data: &[Value],
        settings: &Settings,
        colors: &[&str],
        post_author: &str,
        lines: &mut Vec<String>,
    ) {
        let total_replies = self.count_total_replies(replies_data, settings);
        lines.push(format!("💬 ~ {} replies\n", total_replies));
        lines.push("---\n\n".to_string());

        for reply_obj in replies_data {
            self.process_top_level_reply(reply_obj, settings, colors, post_author, lines);
        }
    }

    fn count_total_replies(&self, replies_data: &[Value], settings: &Settings) -> usize {
        let mut total_replies = replies_data.len();
        for rd in replies_data {
            let replies_extras = get_replies(rd, settings.reply_depth_max);
            total_replies += replies_extras.len();
        }
        total_replies
    }

    fn process_top_level_reply(
        &self,
        reply_obj: &Value,
        settings: &Settings,
        colors: &[&str],
        post_author: &str,
        lines: &mut Vec<String>,
    ) {
        let Some(author) = reply_obj["data"]["author"].as_str() else {
            return;
        };

        if author.is_empty() || (author == "AutoModerator" && !settings.show_auto_mod_comment) {
            return;
        }

        let reply_data = self.extract_reply_data(reply_obj, settings);
        self.add_reply_header(reply_data.clone(), colors, post_author, settings, lines);

        let body = reply_obj["data"]["body"].as_str().unwrap_or("");
        self.process_reply_body(body, author, reply_data.upvotes, settings, lines);

        self.process_child_replies(reply_obj, settings, colors, post_author, lines);

        if settings.line_break_between_parent_replies {
            lines.push("---\n\n".to_string());
        }
    }

    fn extract_reply_data(&self, reply_obj: &Value, settings: &Settings) -> ReplyData {
        let author = reply_obj["data"]["author"].as_str().unwrap_or("");
        let upvotes = reply_obj["data"]["ups"].as_i64().unwrap_or(0) as i32;
        let created_utc = reply_obj["data"]["created_utc"].as_f64().unwrap_or(0.0);
        let timestamp = self.extract_reply_timestamp(created_utc, settings);

        ReplyData {
            author: author.to_string(),
            upvotes,
            timestamp,
        }
    }

    fn extract_reply_timestamp(&self, created_utc: f64, settings: &Settings) -> String {
        if settings.show_timestamp && created_utc > 0.0 {
            if let Some(dt) = chrono::DateTime::from_timestamp(created_utc as i64, 0) {
                dt.format("%Y-%m-%d %H:%M:%S").to_string()
            } else {
                String::new()
            }
        } else {
            String::new()
        }
    }

    fn add_reply_header(
        &self,
        reply_data: ReplyData,
        colors: &[&str],
        post_author: &str,
        settings: &Settings,
        lines: &mut Vec<String>,
    ) {
        let depth_color = if settings.reply_depth_color_indicators {
            colors.first().unwrap_or(&"")
        } else {
            ""
        };

        let upvote_str = format_upvotes(reply_data.upvotes, settings.show_upvotes);
        let author_field = format_author_with_op_marker(&reply_data.author, post_author);
        let timestamp_part = format_timestamp(&reply_data.timestamp, settings.show_timestamp);

        lines.push(format!(
            "* {} **{}** {} {}\n\n",
            depth_color, author_field, upvote_str, timestamp_part
        ));
    }

    fn process_reply_body(
        &self,
        body: &str,
        author: &str,
        upvotes: i32,
        settings: &Settings,
        lines: &mut Vec<String>,
    ) {
        if body.trim().is_empty() {
            return;
        }

        if body == "[deleted]" {
            lines.push("\tComment deleted by user\n\n".to_string());
        } else {
            let filtered_text = apply_filter(
                author,
                body,
                upvotes,
                &settings.filters.keywords,
                &settings.filters.authors,
                settings.filters.min_upvotes,
                &settings.filters.regexes,
                &settings.filtered_message,
            );

            let formatted = format_comment_body(&filtered_text);
            lines.push(format!("\t{}\n\n", formatted));
        }
    }

    fn process_child_replies(
        &self,
        reply_obj: &Value,
        settings: &Settings,
        colors: &[&str],
        post_author: &str,
        lines: &mut Vec<String>,
    ) {
        let child_map = get_replies(reply_obj, settings.reply_depth_max);
        for (_, child_info) in child_map {
            self.process_child_reply(&child_info, settings, colors, post_author, lines);
        }
    }

    fn process_child_reply(
        &self,
        child_info: &HashMap<String, Value>,
        settings: &Settings,
        colors: &[&str],
        post_author: &str,
        lines: &mut Vec<String>,
    ) {
        let cdepth = child_info["depth"].as_i64().unwrap_or(0) as usize;
        let child_reply = &child_info["child_reply"];
        let child_data = &child_reply["data"];

        let child_author = child_data["author"].as_str().unwrap_or("");
        let child_upvotes = child_data["ups"].as_i64().unwrap_or(0) as i32;
        let child_body = child_data["body"].as_str().unwrap_or("");
        let child_created_utc = child_data["created_utc"].as_f64().unwrap_or(0.0);

        let color_symbol = if settings.reply_depth_color_indicators && cdepth < colors.len() {
            colors[cdepth]
        } else {
            ""
        };

        let child_author_field = format_author_with_op_marker(child_author, post_author);
        let child_upvotes_str = format_upvotes(child_upvotes, settings.show_upvotes);
        let child_timestamp = self.extract_reply_timestamp(child_created_utc, settings);
        let child_timestamp_str = format_timestamp(&child_timestamp, settings.show_timestamp);

        let indent = "\t".repeat(cdepth);
        lines.push(format!(
            "{}* {} **{}** {} {}\n\n",
            indent, color_symbol, child_author_field, child_upvotes_str, child_timestamp_str
        ));

        self.process_child_reply_body(
            child_body,
            child_author,
            child_upvotes,
            &indent,
            settings,
            lines,
        );
    }

    fn process_child_reply_body(
        &self,
        child_body: &str,
        child_author: &str,
        child_upvotes: i32,
        indent: &str,
        settings: &Settings,
        lines: &mut Vec<String>,
    ) {
        if child_body.trim().is_empty() {
            return;
        }

        if child_body == "[deleted]" {
            lines.push(format!("{}\tComment deleted by user\n\n", indent));
        } else {
            let filtered_child = apply_filter(
                child_author,
                child_body,
                child_upvotes,
                &settings.filters.keywords,
                &settings.filters.authors,
                settings.filters.min_upvotes,
                &settings.filters.regexes,
                &settings.filtered_message,
            );

            let child_formatted = format_child_comment_body(&filtered_child, indent);
            lines.push(format!("{}\t{}\n\n", indent, child_formatted));
        }
    }
}

#[derive(Clone)]
struct ReplyData {
    author: String,
    upvotes: i32,
    timestamp: String,
}
