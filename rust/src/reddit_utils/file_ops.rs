use anyhow::{Context, Result};
use log::{debug, error, info, warn};
use std::fs;
use std::path::{Path, PathBuf};

pub fn resolve_save_dir(config_directory: &str) -> Result<String> {
    if config_directory == "DEFAULT_REDDIT_SAVE_LOCATION" {
        let directory = std::env::var("DEFAULT_REDDIT_SAVE_LOCATION")
            .context("DEFAULT_REDDIT_SAVE_LOCATION environment variable not set")?;

        if directory.is_empty() {
            return Err(anyhow::anyhow!(
                "DEFAULT_REDDIT_SAVE_LOCATION environment variable is empty"
            ));
        }

        info!(
            "Using default directory from environment variable: {}",
            directory
        );
        Ok(directory)
    } else if !config_directory.is_empty() {
        info!("Using directory set in configuration: {}", config_directory);
        Ok(config_directory.to_string())
    } else {
        println!(
            "Enter the full path to save the post(s). Hit Enter for current dir ({})",
            std::env::current_dir()?.display()
        );

        let mut input = String::new();
        std::io::stdin().read_line(&mut input)?;
        let directory = input.trim();

        let final_dir = if directory.is_empty() {
            std::env::current_dir()?.to_string_lossy().to_string()
        } else {
            directory.to_string()
        };

        while !Path::new(&final_dir).is_dir() {
            error!("Invalid path: '{}'. Try again.", final_dir);
            input.clear();
            std::io::stdin().read_line(&mut input)?;
        }

        info!("User selected directory: {}", final_dir);
        Ok(final_dir)
    }
}

pub fn ensure_dir_exists(path: &str) -> Result<()> {
    let path = Path::new(path);
    if !path.is_dir() {
        debug!("Directory {:?} does not exist, creating...", path);
        fs::create_dir_all(path)?;
    }
    Ok(())
}

pub fn generate_filename(
    base_dir: &str,
    url: &str,
    subreddit: &str,
    use_timestamped_dirs: bool,
    post_timestamp: &str,
    file_format: &str,
    overwrite: bool,
) -> Result<String> {
    debug!(
        "Generating filename: base_dir={}, subreddit={}, format={}",
        base_dir, subreddit, file_format
    );
    let name_candidate = url
        .trim_end_matches('/')
        .split('/')
        .last()
        .unwrap_or(&format!(
            "reddit_no_name_{}",
            chrono::Utc::now().timestamp()
        ))
        .to_string();

    let subreddit = if subreddit.starts_with("r/") {
        &subreddit[2..]
    } else {
        subreddit
    };

    let mut subdir = PathBuf::from(base_dir);
    if !subreddit.is_empty() {
        subdir.push(subreddit);
    }

    if use_timestamped_dirs && !post_timestamp.is_empty() {
        let dt_str = if let Ok(dt) =
            chrono::NaiveDateTime::parse_from_str(post_timestamp, "%Y-%m-%d %H:%M:%S")
        {
            dt.format("%Y-%m-%d").to_string()
        } else {
            chrono::Utc::now().format("%Y-%m-%d").to_string()
        };
        subdir.push(dt_str);
    }

    ensure_dir_exists(subdir.to_str().unwrap())?;

    let ext = if file_format.to_lowercase() == "html" {
        "html"
    } else {
        "md"
    };

    let mut file_path = subdir.join(format!("{}.{}", name_candidate, ext));

    if file_path.exists() {
        debug!("Target file already exists: {:?}", file_path);
        if overwrite {
            warn!(
                "Overwriting existing file: {}",
                file_path.file_name().unwrap().to_string_lossy()
            );
        } else {
            let base_no_ext = file_path.with_extension("");
            let mut suffix = 1;
            loop {
                file_path = base_no_ext.with_file_name(format!(
                    "{}_{}.{}",
                    base_no_ext.file_stem().unwrap().to_string_lossy(),
                    suffix,
                    ext
                ));
                if !file_path.exists() {
                    break;
                }
                suffix += 1;
            }
            debug!(
                "File exists, generated alternative name with suffix {}",
                suffix - 1
            );
            info!(
                "File exists. Using: {}",
                file_path.file_name().unwrap().to_string_lossy()
            );
        }
    }

    let final_path = file_path.to_string_lossy().to_string();
    debug!("Final generated filename: {}", final_path);
    Ok(final_path)
}
