use anyhow::{Context, Result};
use log::{debug, error, info};
use pulldown_cmark::{html, Parser};
use std::fs;
use std::io::Write;

use super::client::get_http_client;

pub fn download_media(url: &str, file_path: &str) -> Result<bool> {
    let client = get_http_client();
    let response = client
        .get(url)
        .send()
        .with_context(|| format!("Failed to download media from {}", url))?;

    if !response.status().is_success() {
        error!("Failed to download media: {}", response.status());
        return Ok(false);
    }

    debug!("Creating file for media content...");
    let mut file = fs::File::create(file_path)
        .with_context(|| format!("Failed to create file: {}", file_path))?;

    let content = response.bytes()?;
    let content_size = content.len();
    debug!("Writing {} bytes of media content...", content_size);
    file.write_all(&content)?;

    info!(
        "Successfully downloaded media to {} ({} bytes)",
        file_path, content_size
    );
    Ok(true)
}

pub fn markdown_to_html(md_content: &str) -> String {
    let parser = Parser::new(md_content);
    let mut html_output = String::new();
    html::push_html(&mut html_output, parser);
    format!("<html><body>{}</body></html>", html_output)
}
