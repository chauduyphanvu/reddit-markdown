use anyhow::{Context, Result};
use csv::Reader;
use log::{error, info, warn};
use rand::seq::SliceRandom;
use serde_json::Value;
use std::fs::File;
use std::io::{self, Write};
use std::path::Path;

use crate::cli_args::CommandLineArgs;
use crate::settings::Settings;

pub struct UrlFetcher {
    base_url: String,
    oauth_base_url: String,
    pub urls: Vec<String>,
}

impl UrlFetcher {
    pub fn new(
        settings: &Settings,
        cli_args: &CommandLineArgs,
        access_token: &str,
    ) -> Result<Self> {
        let mut fetcher = UrlFetcher {
            base_url: "https://www.reddit.com".to_string(),
            oauth_base_url: "https://oauth.reddit.com".to_string(),
            urls: Vec::new(),
        };

        fetcher.collect_urls(settings, cli_args, access_token)?;

        if fetcher.urls.is_empty() {
            fetcher.prompt_for_input(settings, access_token)?;
        }

        Ok(fetcher)
    }

    fn collect_urls(
        &mut self,
        settings: &Settings,
        cli_args: &CommandLineArgs,
        access_token: &str,
    ) -> Result<()> {
        self.urls.extend(cli_args.urls.clone());

        for file_path in &cli_args.src_files {
            self.urls.extend(self.urls_from_file(file_path)?);
        }

        for subreddit in &cli_args.subs {
            self.urls
                .extend(self.get_subreddit_posts(subreddit, false, access_token)?);
        }

        for multi_name in &cli_args.multis {
            if let Some(sub_list) = settings.multi_reddits.get(multi_name) {
                for sub in sub_list {
                    self.urls
                        .extend(self.get_subreddit_posts(sub, false, access_token)?);
                }
            } else {
                warn!("No subreddits found for '{}' in settings.json.", multi_name);
            }
        }

        Ok(())
    }

    fn urls_from_file(&self, file_path: &str) -> Result<Vec<String>> {
        let path = Path::new(file_path);
        if !path.exists() {
            error!("File '{}' not found. Skipping...", file_path);
            return Ok(Vec::new());
        }

        let file = File::open(path)?;
        let mut reader = Reader::from_reader(file);
        let mut result = Vec::new();

        for record in reader.records() {
            let record = record?;
            for field in record.iter() {
                let candidate = field.trim();
                if !candidate.is_empty() {
                    result.push(candidate.to_string());
                }
            }
        }

        Ok(result)
    }

    fn prompt_for_input(&mut self, settings: &Settings, access_token: &str) -> Result<()> {
        println!("Enter/paste the Reddit link(s), comma-separated. Or 'demo', 'surprise', 'r/subreddit', or 'm/multireddit':");
        io::stdout().flush()?;

        let mut input = String::new();
        io::stdin().read_line(&mut input)?;
        let mut user_in = input.trim().to_string();

        while user_in.is_empty() {
            error!("No input provided. Try again.");
            input.clear();
            io::stdin().read_line(&mut input)?;
            user_in = input.trim().to_string();
        }

        self.urls = self.interpret_input_mode(&user_in, settings, access_token)?;
        Ok(())
    }

    fn interpret_input_mode(
        &self,
        user_in: &str,
        settings: &Settings,
        access_token: &str,
    ) -> Result<Vec<String>> {
        let lower_in = user_in.to_lowercase();

        if lower_in == "demo" {
            info!("Demo mode enabled.");
            return Ok(vec![
                "https://www.reddit.com/r/pcmasterrace/comments/101kjyq/my_dad_has_been_playing_civilization_almost_daily/".to_string()
            ]);
        } else if lower_in == "surprise" {
            info!("Surprise mode enabled. Grabbing one random post from r/popular.");
            return self.fetch_posts_from_sub("r/popular", true, false, access_token);
        } else if user_in.starts_with("r/") {
            info!("Subreddit mode: fetching best posts from {} ...", user_in);
            return self.get_subreddit_posts(user_in, true, access_token);
        } else if user_in.starts_with("m/") {
            info!(
                "Multireddit mode: attempting to fetch subreddits from settings for {} ...",
                user_in
            );
            let mut results = Vec::new();
            if let Some(subs) = settings.multi_reddits.get(user_in) {
                for s in subs {
                    results.extend(self.get_subreddit_posts(s, true, access_token)?);
                }
            }
            return Ok(results);
        } else {
            return Ok(user_in
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect());
        }
    }

    fn get_subreddit_posts(
        &self,
        subreddit_str: &str,
        best: bool,
        access_token: &str,
    ) -> Result<Vec<String>> {
        self.fetch_posts_from_sub(subreddit_str, false, best, access_token)
    }

    fn fetch_posts_from_sub(
        &self,
        subreddit_str: &str,
        pick_random: bool,
        best: bool,
        access_token: &str,
    ) -> Result<Vec<String>> {
        let subreddit_str = subreddit_str.trim_start_matches('/');

        let base = if !access_token.is_empty() {
            &self.oauth_base_url
        } else {
            &self.base_url
        };

        let mut url = format!("{}/{}", base, subreddit_str);
        if best {
            url.push_str("/best");
        }

        let json_data = self.download_post_json(&url, access_token)?;

        let children = json_data
            .get("data")
            .and_then(|d| d.get("children"))
            .and_then(|c| c.as_array())
            .ok_or_else(|| anyhow::anyhow!("Unable to parse subreddit data"))?;

        let mut post_links = Vec::new();
        for child in children {
            if let Some(permalink) = child
                .get("data")
                .and_then(|d| d.get("permalink"))
                .and_then(|p| p.as_str())
            {
                post_links.push(format!("{}{}", self.base_url, permalink));
            }
        }

        if pick_random && !post_links.is_empty() {
            let mut rng = rand::thread_rng();
            if let Some(chosen) = post_links.choose(&mut rng) {
                return Ok(vec![chosen.clone()]);
            }
        }

        Ok(post_links)
    }

    fn download_post_json(&self, url: &str, access_token: &str) -> Result<Value> {
        let json_url = if url.ends_with(".json") {
            url.to_string()
        } else {
            format!("{}.json", url)
        };

        let client = reqwest::blocking::Client::new();
        let mut request = client
            .get(&json_url)
            .header("User-Agent", "MyRedditScript/0.1")
            .timeout(std::time::Duration::from_secs(10));

        if !access_token.is_empty() {
            request = request.header("Authorization", format!("bearer {}", access_token));
        }

        let response = request
            .send()
            .with_context(|| format!("Failed to download JSON data for {}", url))?;

        if !response.status().is_success() {
            return Err(anyhow::anyhow!(
                "Failed to download JSON data: {}",
                response.status()
            ));
        }

        let json: Value = response.json()?;
        Ok(json)
    }
}
