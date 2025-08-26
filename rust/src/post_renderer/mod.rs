use anyhow::Result;
use serde_json::Value;

mod content_builder;
mod formatting;
mod media_handler;
mod reply_processor;

pub use content_builder::build_post_content;
use content_builder::PostContentBuilder;

pub struct PostRenderer {
    builder: PostContentBuilder,
}

impl PostRenderer {
    pub fn new() -> Self {
        Self {
            builder: PostContentBuilder::new(),
        }
    }

    pub fn build_post(
        &mut self,
        post_data: &Value,
        replies_data: &[Value],
        settings: &crate::settings::Settings,
        colors: &[&str],
        url: &str,
        target_path: &str,
    ) -> Result<String> {
        self.builder
            .build_post_content(post_data, replies_data, settings, colors, url, target_path)
    }
}
