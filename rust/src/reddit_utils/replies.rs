use log::debug;
use serde_json::Value;
use std::collections::HashMap;

pub fn get_replies(reply_data: &Value, max_depth: i32) -> HashMap<String, HashMap<String, Value>> {
    debug!("Processing replies with max_depth: {}", max_depth);
    let mut collected = HashMap::with_capacity(16); // Pre-allocate with reasonable capacity

    let children = reply_data
        .pointer("/data/replies")
        .and_then(|r| r.pointer("/data/children"))
        .and_then(|c| c.as_array());

    if let Some(children) = children {
        for child in children {
            let child_id = child
                .get("data")
                .and_then(|d| d.get("id"))
                .and_then(|id| id.as_str())
                .unwrap_or("")
                .to_string();

            let child_depth = child
                .get("data")
                .and_then(|d| d.get("depth"))
                .and_then(|d| d.as_i64())
                .unwrap_or(0) as i32;

            let child_body = child
                .get("data")
                .and_then(|d| d.get("body"))
                .and_then(|b| b.as_str())
                .unwrap_or("");

            if max_depth != -1 && child_depth > max_depth {
                continue;
            }

            if child_body.trim().is_empty() {
                continue;
            }

            let mut child_info = HashMap::new();
            child_info.insert("depth".to_string(), Value::from(child_depth));
            child_info.insert("child_reply".to_string(), child.clone());

            collected.insert(child_id.clone(), child_info);

            let nested_replies = get_replies(child, max_depth);
            collected.extend(nested_replies);
        }
    }

    debug!("Collected {} reply entries", collected.len());
    collected
}
