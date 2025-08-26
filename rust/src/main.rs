mod auth;
mod cli_args;
mod filters;
mod post_renderer;
mod reddit_utils;
mod settings;
mod url_fetcher;

use anyhow::Result;
use indicatif::{ProgressBar, ProgressStyle};
use log::{debug, error, info, warn};
use std::fs;
use std::path::Path;
use std::thread;
use std::time::{Duration, Instant};

use cli_args::CommandLineArgs;
use post_renderer::build_post_content;
use reddit_utils::{clean_url, download_post_json, generate_filename, resolve_save_dir, valid_url};
use settings::Settings;
use url_fetcher::UrlFetcher;

fn main() -> Result<()> {
    env_logger::Builder::from_default_env()
        .filter_level(log::LevelFilter::Info)
        .init();

    let start_time = Instant::now();
    info!(
        "Reddit Markdown Tool v{} starting up...",
        env!("CARGO_PKG_VERSION")
    );

    debug!("Loading application settings...");
    let settings = load_settings()?;
    info!("Settings loaded successfully");

    let mut access_token = String::new();
    debug!("Initializing access token...");

    if settings.auth.login_on_startup {
        info!("Attempting Reddit authentication...");
        match auth::get_access_token(&settings.auth.client_id, &settings.auth.client_secret) {
            Ok(token) => {
                access_token = token;
                info!("Reddit authentication successful");
            }
            Err(e) => {
                warn!("Could not log in. Proceeding without authentication: {}", e);
            }
        }
    } else {
        debug!("Skipping authentication (login_on_startup = false)");
    }

    debug!("Parsing command line arguments...");
    let cli_args = CommandLineArgs::parse_args();
    info!("Command line arguments parsed successfully");

    info!("Fetching URLs to process...");
    let all_urls = fetch_urls(&settings, &cli_args, &access_token)?;
    info!("Found {} URLs to process", all_urls.len());

    debug!("Resolving save directory...");
    let base_save_dir = resolve_save_dir(&settings.default_save_location)?;
    info!("Save directory resolved: {}", base_save_dir);

    process_all_urls(all_urls, &settings, &base_save_dir, &access_token)?;

    let elapsed = start_time.elapsed();
    info!(
        "Processing completed in {:.2} seconds",
        elapsed.as_secs_f64()
    );
    info!("Thanks for using this script!");
    info!("If you have issues, open an issue on GitHub:");
    info!("https://github.com/chauduyphanvu/reddit-markdown/issues");

    Ok(())
}

fn load_settings() -> Result<Settings> {
    let settings = Settings::load("../settings.json")?;

    if settings.update_check_on_startup {
        if let Err(e) = settings.check_for_updates() {
            warn!("Failed to check for updates: {}", e);
        }
    }

    Ok(settings)
}

fn fetch_urls(
    settings: &Settings,
    cli_args: &CommandLineArgs,
    access_token: &str,
) -> Result<Vec<String>> {
    let fetcher = UrlFetcher::new(settings, cli_args, access_token)?;
    Ok(fetcher
        .urls
        .into_iter()
        .filter_map(|u| {
            let cleaned = clean_url(&u);
            if cleaned.is_empty() {
                None
            } else {
                Some(cleaned)
            }
        })
        .collect())
}

fn process_all_urls(
    all_urls: Vec<String>,
    settings: &Settings,
    base_save_dir: &str,
    access_token: &str,
) -> Result<()> {
    let colors = vec!["🟩", "🟨", "🟧", "🟦", "🟪", "🟥", "🟫", "⬛️", "⬜️"];
    let total_urls = all_urls.len();

    info!("Starting to process {} Reddit posts...", total_urls);
    let pb = create_progress_bar(total_urls);

    let (successful_count, failed_count) = process_urls_with_progress(
        &all_urls,
        settings,
        base_save_dir,
        &colors,
        access_token,
        &pb,
    );

    finish_processing(&pb, successful_count, failed_count, total_urls);
    Ok(())
}

fn create_progress_bar(total_urls: usize) -> ProgressBar {
    let pb = ProgressBar::new(total_urls as u64);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{elapsed_precise}] [{wide_bar:.cyan/blue}] {pos}/{len} ({eta}) {msg}")
            .unwrap()
            .progress_chars("#>-")
    );
    pb
}

fn process_urls_with_progress(
    all_urls: &[String],
    settings: &Settings,
    base_save_dir: &str,
    colors: &[&str],
    access_token: &str,
    pb: &ProgressBar,
) -> (usize, usize) {
    let mut successful_count = 0;
    let mut failed_count = 0;
    let total_urls = all_urls.len();

    for (i, url) in all_urls.iter().enumerate() {
        let post_num = i + 1;
        update_progress_message(pb, post_num, total_urls, url);

        match process_single_url(
            post_num,
            url,
            total_urls,
            settings,
            base_save_dir,
            colors,
            access_token,
        ) {
            Ok(()) => {
                successful_count += 1;
                debug!(
                    "Successfully processed post {}/{}: {}",
                    post_num, total_urls, url
                );
            }
            Err(e) => {
                failed_count += 1;
                error!(
                    "Failed to process post {}/{}: {} - Error: {}",
                    post_num, total_urls, url, e
                );
            }
        }

        pb.inc(1);
        thread::sleep(Duration::from_secs(1));
    }

    (successful_count, failed_count)
}

fn update_progress_message(pb: &ProgressBar, post_num: usize, total_urls: usize, url: &str) {
    pb.set_message(format!(
        "Processing post {}/{}: {}",
        post_num,
        total_urls,
        if url.len() > 50 {
            format!("{}...", &url[..47])
        } else {
            url.to_string()
        }
    ));
}

fn finish_processing(
    pb: &ProgressBar,
    successful_count: usize,
    failed_count: usize,
    total_urls: usize,
) {
    pb.finish_with_message(format!(
        "Completed! {} successful, {} failed",
        successful_count, failed_count
    ));

    if failed_count > 0 {
        warn!(
            "Processing completed with {} failed posts out of {}",
            failed_count, total_urls
        );
    } else {
        info!("All {} posts processed successfully!", total_urls);
    }
}

fn process_single_url(
    index: usize,
    url: &str,
    total: usize,
    settings: &Settings,
    base_save_dir: &str,
    colors: &[&str],
    access_token: &str,
) -> Result<()> {
    let start_time = Instant::now();

    if !valid_url(url) {
        warn!("Invalid post URL '{}'. Skipping...", url);
        return Ok(());
    }

    debug!("Processing post {} of {}: {}", index, total, url);

    let post_data = fetch_and_parse_post_data(url, access_token)?;
    let target_path = generate_target_path(&post_data, base_save_dir, url, settings)?;
    let content = build_and_format_content(&post_data, settings, colors, url, &target_path)?;

    write_to_file(&target_path, &content)?;

    log_completion(&post_data, &target_path, start_time);
    Ok(())
}

struct PostData {
    data: serde_json::Value,
    replies: Vec<serde_json::Value>,
    title: String,
    subreddit: String,
    timestamp: String,
}

fn fetch_and_parse_post_data(url: &str, access_token: &str) -> Result<PostData> {
    debug!("Downloading JSON data for post: {}", url);
    let data = download_post_json(url, access_token)?;
    debug!("JSON data downloaded successfully");

    debug!("Parsing post data structure...");
    let data_array = data
        .as_array()
        .ok_or_else(|| anyhow::anyhow!("Invalid post data structure"))?;

    if data_array.len() < 2 {
        return Err(anyhow::anyhow!(
            "Could not fetch or parse post data for {}. Invalid structure",
            url
        ));
    }

    let post_info = data_array[0]["data"]["children"]
        .as_array()
        .ok_or_else(|| anyhow::anyhow!("No post info found"))?;

    if post_info.is_empty() {
        return Err(anyhow::anyhow!("No post info found for {}", url));
    }

    let post_data_json = &post_info[0]["data"];
    let replies_data = data_array[1]["data"]["children"]
        .as_array()
        .map(|v| v.clone())
        .unwrap_or_default();

    let title = post_data_json["title"]
        .as_str()
        .unwrap_or("Untitled")
        .to_string();
    let subreddit = post_data_json["subreddit_name_prefixed"]
        .as_str()
        .unwrap_or("unknown")
        .to_string();

    debug!("Processing post '{}' from {}", title, subreddit);
    debug!("Found {} replies to process", replies_data.len());

    let timestamp = extract_timestamp(post_data_json);

    Ok(PostData {
        data: post_data_json.clone(),
        replies: replies_data,
        title,
        subreddit,
        timestamp,
    })
}

fn extract_timestamp(post_data: &serde_json::Value) -> String {
    if let Some(created_utc) = post_data["created_utc"].as_f64() {
        if let Some(dt) = chrono::DateTime::from_timestamp(created_utc as i64, 0) {
            dt.format("%Y-%m-%d %H:%M:%S").to_string()
        } else {
            String::new()
        }
    } else {
        String::new()
    }
}

fn generate_target_path(
    post_data: &PostData,
    base_save_dir: &str,
    url: &str,
    settings: &Settings,
) -> Result<String> {
    debug!("Generating filename for post...");
    let target_path = generate_filename(
        base_save_dir,
        url,
        &post_data.subreddit,
        settings.use_timestamped_directories,
        &post_data.timestamp,
        &settings.file_format,
        settings.overwrite_existing_file,
    )?;
    debug!("Target file path: {}", target_path);
    Ok(target_path)
}

fn build_and_format_content(
    post_data: &PostData,
    settings: &Settings,
    colors: &[&str],
    url: &str,
    target_path: &str,
) -> Result<String> {
    debug!("Building post content...");
    let content_start = Instant::now();
    let raw_markdown = build_post_content(
        &post_data.data,
        &post_data.replies,
        settings,
        colors,
        url,
        target_path,
    )?;
    debug!(
        "Content built in {:.2}ms",
        content_start.elapsed().as_secs_f64() * 1000.0
    );

    let final_content = if settings.file_format.to_lowercase() == "html" {
        debug!("Converting markdown to HTML...");
        markdown_to_html(&raw_markdown)
    } else {
        raw_markdown
    };

    Ok(final_content)
}

fn log_completion(post_data: &PostData, target_path: &str, start_time: Instant) {
    let elapsed = start_time.elapsed();
    info!(
        "Reddit post '{}' saved at {} (processed in {:.2}s)",
        post_data.title,
        target_path,
        elapsed.as_secs_f64()
    );
}

fn write_to_file(file_path: &str, content: &str) -> Result<()> {
    let path = Path::new(file_path);

    if let Some(parent) = path.parent() {
        debug!("Creating directory structure: {:?}", parent);
        fs::create_dir_all(parent)?;
    }

    debug!("Writing {} bytes to file: {}", content.len(), file_path);
    fs::write(path, content)?;
    debug!("File written successfully");
    Ok(())
}

fn markdown_to_html(md_content: &str) -> String {
    use pulldown_cmark::{html, Parser};

    let parser = Parser::new(md_content);
    let mut html_output = String::new();
    html::push_html(&mut html_output, parser);

    format!(
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body>{}</body></html>",
        html_output
    )
}
