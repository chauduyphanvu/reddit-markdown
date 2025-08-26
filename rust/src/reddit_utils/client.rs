use std::sync::OnceLock;

static HTTP_CLIENT: OnceLock<reqwest::blocking::Client> = OnceLock::new();

pub fn get_http_client() -> &'static reqwest::blocking::Client {
    HTTP_CLIENT.get_or_init(|| {
        reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .user_agent("MyRedditScript/0.1")
            .build()
            .expect("Failed to create HTTP client")
    })
}
