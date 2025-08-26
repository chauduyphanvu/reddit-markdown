use anyhow::Result;
use serde_json::Value;
use std::path::Path;

use crate::reddit_utils::{download_media, ensure_dir_exists};

pub struct MediaHandler;

impl MediaHandler {
    pub fn process_media(
        &self,
        post_data: &Value,
        target_path: &str,
        lines: &mut Vec<String>,
    ) -> Result<()> {
        let target_dir = Path::new(target_path).parent().unwrap_or(Path::new("."));
        let media_path = target_dir.join("media");

        if self.is_gallery(post_data)? {
            self.process_gallery(post_data, &media_path, lines)?;
        } else if self.is_video(post_data)? {
            self.process_video(post_data, &media_path, lines)?;
        } else if self.has_oembed(post_data) {
            self.process_oembed(post_data, lines);
        } else if self.is_single_image(post_data)? {
            self.process_single_image(post_data, &media_path, lines)?;
        }

        Ok(())
    }

    fn is_gallery(&self, post_data: &Value) -> Result<bool> {
        Ok(post_data["is_gallery"].as_bool().unwrap_or(false))
    }

    fn is_video(&self, post_data: &Value) -> Result<bool> {
        Ok(post_data["is_video"].as_bool().unwrap_or(false))
    }

    fn has_oembed(&self, post_data: &Value) -> bool {
        post_data["media"]["oembed"]["html"].as_str().is_some()
    }

    fn is_single_image(&self, post_data: &Value) -> Result<bool> {
        Ok(post_data["post_hint"].as_str() == Some("image"))
    }

    fn process_gallery(
        &self,
        post_data: &Value,
        media_path: &Path,
        lines: &mut Vec<String>,
    ) -> Result<()> {
        if let Some(gallery_items) = post_data["gallery_data"]["items"].as_array() {
            if let Some(media_metadata) = post_data["media_metadata"].as_object() {
                ensure_dir_exists(media_path.to_str().unwrap())?;
                lines.push("### Image Gallery\n".to_string());

                for item in gallery_items {
                    if let Some(media_id) = item["media_id"].as_str() {
                        if let Some(meta) = media_metadata.get(media_id) {
                            self.process_gallery_item(meta, media_path, lines)?;
                        }
                    }
                }
                lines.push("\n".to_string());
            }
        }
        Ok(())
    }

    fn process_gallery_item(
        &self,
        meta: &Value,
        media_path: &Path,
        lines: &mut Vec<String>,
    ) -> Result<()> {
        if meta["e"].as_str() == Some("Image") {
            if let Some(img_url) = meta["s"]["u"].as_str() {
                let img_url = img_url.replace("&amp;", "&");
                let img_filename = Path::new(&img_url)
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .to_string();
                let local_img_path = media_path.join(&img_filename);

                if download_media(&img_url, local_img_path.to_str().unwrap()).unwrap_or(false) {
                    lines.push(format!("![](./media/{})\n\n", img_filename));
                }
            }
        }
        Ok(())
    }

    fn process_video(
        &self,
        post_data: &Value,
        media_path: &Path,
        lines: &mut Vec<String>,
    ) -> Result<()> {
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
        Ok(())
    }

    fn process_oembed(&self, post_data: &Value, lines: &mut Vec<String>) {
        if let Some(oembed_html) = post_data["media"]["oembed"]["html"].as_str() {
            lines.push(format!(
                "{}\n",
                html_escape::decode_html_entities(oembed_html)
            ));
        }
    }

    fn process_single_image(
        &self,
        post_data: &Value,
        media_path: &Path,
        lines: &mut Vec<String>,
    ) -> Result<()> {
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
        Ok(())
    }
}
