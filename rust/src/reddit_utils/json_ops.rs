use anyhow::{Context, Result};
use log::{debug, error};
use serde_json::Value;

use super::client::get_http_client;

pub fn download_post_json(url: &str, access_token: &str) -> Result<Value> {
    let json_url = if url.ends_with(".json") {
        url.to_string()
    } else {
        format!("{}.json", url)
    };

    debug!("Fetching Reddit post JSON from: {}", json_url);

    let client = get_http_client();
    let mut request = client.get(&json_url);

    let _final_url = if !access_token.is_empty() {
        let oauth_url = json_url.replace("https://www.reddit.com", "https://oauth.reddit.com");
        debug!("Using OAuth endpoint: {}", oauth_url);
        request = client
            .get(&oauth_url)
            .header("Authorization", format!("bearer {}", access_token));
        oauth_url
    } else {
        debug!("Using public endpoint (no authentication)");
        json_url
    };

    debug!("Sending HTTP request...");
    let response = request
        .send()
        .with_context(|| format!("Failed to download JSON for {}", url))?;

    debug!("Received response with status: {}", response.status());

    if !response.status().is_success() {
        error!("HTTP request failed with status: {}", response.status());
        return Err(anyhow::anyhow!(
            "Failed to fetch post data: {}",
            response.status()
        ));
    }

    debug!("Parsing JSON response...");
    let json: Value = response
        .json()
        .with_context(|| format!("Failed to parse JSON for {}", url))?;

    debug!("JSON parsed successfully, {} bytes", json.to_string().len());

    Ok(json)
}
