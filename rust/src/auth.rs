use anyhow::{Context, Result};
use log::{error, info};
use serde::Deserialize;
use std::collections::HashMap;

#[derive(Debug, Deserialize)]
struct AccessTokenResponse {
    access_token: String,
    token_type: String,
    expires_in: i64,
}

pub fn get_access_token(client_id: &str, client_secret: &str) -> Result<String> {
    let client = reqwest::blocking::Client::new();

    let mut params = HashMap::new();
    params.insert("grant_type", "client_credentials");

    let response = client
        .post("https://www.reddit.com/api/v1/access_token")
        .basic_auth(client_id, Some(client_secret))
        .header("User-Agent", "MyRedditScript/0.1")
        .form(&params)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .context("Failed to send authentication request")?;

    if !response.status().is_success() {
        error!("Failed to authenticate with Reddit: {}", response.status());
        return Err(anyhow::anyhow!(
            "Authentication failed with status: {}",
            response.status()
        ));
    }

    let token_response: AccessTokenResponse = response
        .json()
        .context("Failed to parse authentication response")?;

    if token_response.access_token.is_empty() {
        error!("Failed to retrieve access token. Response was empty");
        return Err(anyhow::anyhow!("Empty access token received"));
    }

    info!("Successfully authenticated with Reddit.");
    Ok(token_response.access_token)
}
