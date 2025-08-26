use regex::Regex;

pub fn format_timestamp(timestamp: &str, show_timestamp: bool) -> String {
    if show_timestamp && !timestamp.is_empty() {
        format!("_( {} )_", timestamp)
    } else {
        String::new()
    }
}

pub fn format_upvotes(upvotes: i32, show_upvotes: bool) -> String {
    if show_upvotes && upvotes > 0 {
        if upvotes >= 1000 {
            format!("⬆️ {}k", upvotes / 1000)
        } else {
            format!("⬆️ {}", upvotes)
        }
    } else {
        String::new()
    }
}

pub fn format_author_link(author: &str) -> String {
    if !author.is_empty() && author != "[deleted]" {
        format!("[{}](https://www.reddit.com/user/{})", author, author)
    } else {
        author.to_string()
    }
}

pub fn format_author_with_op_marker(author: &str, post_author: &str) -> String {
    let author_link = format_author_link(author);
    if author == post_author && !author_link.is_empty() {
        format!("{} (OP)", author_link)
    } else {
        author_link
    }
}

thread_local! {
    static USER_RE: Regex = Regex::new(r"u/(\w+)").unwrap();
}

pub fn format_comment_body(body: &str) -> String {
    USER_RE.with(|re| {
        let temp = body
            .replace("&gt;", ">")
            .replace("\n", "\n\t")
            .replace('\r', "");
        re.replace_all(&temp, r"[u/$1](https://www.reddit.com/user/$1)")
            .into_owned()
    })
}

pub fn format_child_comment_body(body: &str, indent: &str) -> String {
    USER_RE.with(|re| {
        let mut formatted = body
            .replace("&gt;", ">")
            .replace("&#32;", " ")
            .replace("^^[", "[")
            .replace("^^(", "(");

        formatted = re
            .replace_all(&formatted, r"[u/$1](https://www.reddit.com/user/$1)")
            .into_owned();

        formatted.replace('\n', &format!("\n{}\t", indent))
    })
}

pub fn escape_selftext(text: &str) -> String {
    text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
}
