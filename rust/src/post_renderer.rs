use anyhow::Result;
use chrono::NaiveDateTime;
use log::{debug, info, warn};
use regex::Regex;
use serde_json::Value;
use std::collections::HashMap;
use std::path::Path;

use crate::filters::apply_filter;
use crate::reddit_utils::{download_media, ensure_dir_exists, get_replies};
use crate::settings::Settings;

pub fn build_post_content(
    post_data: &Value,
    replies_data: &[Value],
    settings: &Settings,
    colors: &[&str],
    _url: &str,
    target_path: &str,
) -> Result<String> {
    let post_title = post_data["title"].as_str().unwrap_or("Untitled");
    debug!("Building content for post: '{}'", post_title);
    let post_author = post_data["author"].as_str().unwrap_or("[unknown]");
    let subreddit = post_data["subreddit_name_prefixed"].as_str().unwrap_or("");
    let post_ups = post_data["ups"].as_i64().unwrap_or(0) as i32;
    let post_locked = post_data["locked"].as_bool().unwrap_or(false);
    let post_selftext = post_data["selftext"].as_str().unwrap_or("");
    let post_url = post_data["url"].as_str().unwrap_or("");
    let created_utc = post_data["created_utc"].as_f64();

    let post_timestamp = if let Some(timestamp) = created_utc {
        let dt = NaiveDateTime::from_timestamp_opt(timestamp as i64, 0)
            .unwrap_or_else(|| NaiveDateTime::from_timestamp_opt(0, 0).unwrap());
        dt.format("%Y-%m-%d %H:%M:%S").to_string()
    } else {
        String::new()
    };

    let upvotes_display = if settings.show_upvotes && post_ups > 0 {
        if post_ups >= 1000 {
            format!("⬆️ {}k", post_ups / 1000)
        } else {
            format!("⬆️ {}", post_ups)
        }
    } else {
        String::new()
    };

    let timestamp_display = if settings.show_timestamp && !post_timestamp.is_empty() {
        format!("_( {} )_", post_timestamp)
    } else {
        String::new()
    };

    let lock_msg = if post_locked {
        format!(
            "---\n\n>🔒 **This thread has been locked by the moderators of {}**.\n  New comments cannot be posted\n\n",
            subreddit
        )
    } else {
        String::new()
    };

    let mut lines = Vec::new();

    lines.push(format!(
        "**{}** | Posted by u/{} {} {}\n",
        subreddit, post_author, upvotes_display, timestamp_display
    ));
    lines.push(format!("## {}\n", post_title));
    lines.push(format!("Original post: [{}]({})\n", post_url, post_url));

    if !lock_msg.is_empty() {
        lines.push(lock_msg);
    }

    if !post_selftext.is_empty() {
        let selftext_escaped = post_selftext
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"");
        lines.push(format!("> {}\n", selftext_escaped.replace('\n', "\n> ")));
    }

    if settings.enable_media_downloads {
        let target_dir = Path::new(target_path).parent().unwrap_or(Path::new("."));
        let media_path = target_dir.join("media");

        if post_data["is_gallery"].as_bool().unwrap_or(false) {
            if let Some(gallery_items) = post_data["gallery_data"]["items"].as_array() {
                if let Some(media_metadata) = post_data["media_metadata"].as_object() {
                    ensure_dir_exists(media_path.to_str().unwrap())?;
                    lines.push("### Image Gallery\n".to_string());

                    for item in gallery_items {
                        if let Some(media_id) = item["media_id"].as_str() {
                            if let Some(meta) = media_metadata.get(media_id) {
                                if meta["e"].as_str() == Some("Image") {
                                    if let Some(img_url) = meta["s"]["u"].as_str() {
                                        let img_url = img_url.replace("&amp;", "&");
                                        let img_filename = Path::new(&img_url)
                                            .file_name()
                                            .unwrap_or_default()
                                            .to_string_lossy()
                                            .to_string();
                                        let local_img_path = media_path.join(&img_filename);

                                        if download_media(
                                            &img_url,
                                            local_img_path.to_str().unwrap(),
                                        )
                                        .unwrap_or(false)
                                        {
                                            lines
                                                .push(format!("![](./media/{})\n\n", img_filename));
                                        }
                                    }
                                }
                            }
                        }
                    }
                    lines.push("\n".to_string());
                }
            }
        } else if post_data["is_video"].as_bool().unwrap_or(false) {
            if let Some(video_url) = post_data["media"]["reddit_video"]["fallback_url"].as_str() {
                ensure_dir_exists(media_path.to_str().unwrap())?;
                let video_filename = Path::new(video_url)
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .to_string();
                let local_video_path = media_path.join(&video_filename);

                if download_media(video_url, local_video_path.to_str().unwrap()).unwrap_or(false) {
                    lines.push(format!(
                        "<video controls src=\"./media/{}\"></video>\n",
                        video_filename
                    ));
                }
            }
        } else if let Some(oembed_html) = post_data["media"]["oembed"]["html"].as_str() {
            lines.push(format!(
                "{}\n",
                html_escape::decode_html_entities(oembed_html)
            ));
        } else if post_data["post_hint"].as_str() == Some("image") {
            if let Some(image_url) = post_data["url"].as_str() {
                ensure_dir_exists(media_path.to_str().unwrap())?;
                let img_filename = Path::new(image_url)
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .to_string();
                let local_img_path = media_path.join(&img_filename);

                if download_media(image_url, local_img_path.to_str().unwrap()).unwrap_or(false) {
                    lines.push(format!("![](./media/{})\n", img_filename));
                }
            }
        }
    }

    let mut total_replies = replies_data.len();
    for rd in replies_data {
        let replies_extras = get_replies(rd, settings.reply_depth_max);
        total_replies += replies_extras.len();
    }

    lines.push(format!("💬 ~ {} replies\n", total_replies));
    lines.push("---\n\n".to_string());

    for reply_obj in replies_data {
        let Some(author) = reply_obj["data"]["author"].as_str() else {
            continue;
        };

        if author.is_empty() {
            continue;
        }

        if author == "AutoModerator" && !settings.show_auto_mod_comment {
            continue;
        }

        let depth_color = if settings.reply_depth_color_indicators {
            colors.first().unwrap_or(&"")
        } else {
            ""
        };

        let reply_ups = reply_obj["data"]["ups"].as_i64().unwrap_or(0) as i32;
        let upvote_str = if settings.show_upvotes && reply_ups > 0 {
            if reply_ups >= 1000 {
                format!("⬆️ {}k", reply_ups / 1000)
            } else {
                format!("⬆️ {}", reply_ups)
            }
        } else {
            String::new()
        };

        let created_utc = reply_obj["data"]["created_utc"].as_f64().unwrap_or(0.0);
        let top_reply_timestamp = if settings.show_timestamp && created_utc > 0.0 {
            let dt = NaiveDateTime::from_timestamp_opt(created_utc as i64, 0)
                .unwrap_or_else(|| NaiveDateTime::from_timestamp_opt(0, 0).unwrap());
            dt.format("%Y-%m-%d %H:%M:%S").to_string()
        } else {
            String::new()
        };

        let author_field = if author != "[deleted]" {
            format!("[{}](https://www.reddit.com/user/{})", author, author)
        } else {
            author.to_string()
        };

        let author_field = if author == post_author {
            format!("{} (OP)", author_field)
        } else {
            author_field
        };

        let timestamp_part = if !top_reply_timestamp.is_empty() {
            format!("_( {} )_", top_reply_timestamp)
        } else {
            String::new()
        };

        lines.push(format!(
            "* {} **{}** {} {}\n\n",
            depth_color, author_field, upvote_str, timestamp_part
        ));

        let body = reply_obj["data"]["body"].as_str().unwrap_or("");
        if body.trim().is_empty() {
            continue;
        }

        if body == "[deleted]" {
            lines.push("\tComment deleted by user\n\n".to_string());
        } else {
            let filtered_text = apply_filter(
                author,
                body,
                reply_ups,
                &settings.filters.keywords,
                &settings.filters.authors,
                settings.filters.min_upvotes,
                &settings.filters.regexes,
                &settings.filtered_message,
            );

            let formatted = filtered_text
                .replace("&gt;", ">")
                .replace("\n", "\n\t")
                .replace('\r', "");

            let re = Regex::new(r"u/(\w+)").unwrap();
            let formatted = re.replace_all(&formatted, r"[u/$1](https://www.reddit.com/user/$1)");

            lines.push(format!("\t{}\n\n", formatted));
        }

        let child_map = get_replies(reply_obj, settings.reply_depth_max);
        for (_, child_info) in child_map {
            let cdepth = child_info["depth"].as_i64().unwrap_or(0) as usize;
            let child_reply = &child_info["child_reply"];
            let child_data = &child_reply["data"];

            let child_author = child_data["author"].as_str().unwrap_or("");
            let child_ups = child_data["ups"].as_i64().unwrap_or(0) as i32;
            let child_body = child_data["body"].as_str().unwrap_or("");
            let child_created_utc = child_data["created_utc"].as_f64().unwrap_or(0.0);

            let color_symbol = if settings.reply_depth_color_indicators && cdepth < colors.len() {
                colors[cdepth]
            } else {
                ""
            };

            let child_author_field = if !child_author.is_empty() && child_author != "[deleted]" {
                format!(
                    "[{}](https://www.reddit.com/user/{})",
                    child_author, child_author
                )
            } else {
                child_author.to_string()
            };

            let child_author_field =
                if child_author == post_author && !child_author_field.is_empty() {
                    format!("{} (OP)", child_author_field)
                } else {
                    child_author_field
                };

            let child_ups_str = if settings.show_upvotes && child_ups > 0 {
                if child_ups >= 1000 {
                    format!("⬆️ {}k", child_ups / 1000)
                } else {
                    format!("⬆️ {}", child_ups)
                }
            } else {
                String::new()
            };

            let child_ts = if settings.show_timestamp && child_created_utc > 0.0 {
                let dt = NaiveDateTime::from_timestamp_opt(child_created_utc as i64, 0)
                    .unwrap_or_else(|| NaiveDateTime::from_timestamp_opt(0, 0).unwrap());
                format!("_( {} )_", dt.format("%Y-%m-%d %H:%M:%S"))
            } else {
                String::new()
            };

            let indent = "\t".repeat(cdepth);
            lines.push(format!(
                "{}* {} **{}** {} {}\n\n",
                indent, color_symbol, child_author_field, child_ups_str, child_ts
            ));

            if child_body.trim().is_empty() {
                continue;
            }

            if child_body == "[deleted]" {
                lines.push(format!("{}\tComment deleted by user\n\n", indent));
            } else {
                let filtered_child = apply_filter(
                    child_author,
                    child_body,
                    child_ups,
                    &settings.filters.keywords,
                    &settings.filters.authors,
                    settings.filters.min_upvotes,
                    &settings.filters.regexes,
                    &settings.filtered_message,
                );

                let mut child_formatted = filtered_child
                    .replace("&gt;", ">")
                    .replace("&amp;#32;", " ")
                    .replace("^^[", "[")
                    .replace("^^(", "(");

                let re = Regex::new(r"u/(\w+)").unwrap();
                child_formatted = re
                    .replace_all(&child_formatted, r"[u/$1](https://www.reddit.com/user/$1)")
                    .to_string();
                child_formatted = child_formatted.replace('\n', &format!("\n{}\t", indent));

                lines.push(format!("{}\t{}\n\n", indent, child_formatted));
            }
        }

        if settings.line_break_between_parent_replies {
            lines.push("---\n\n".to_string());
        }
    }

    lines.push("\n".to_string());
    Ok(lines.join(""))
}
