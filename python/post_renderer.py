import datetime
import logging
import re
from typing import Any, Dict, List

import reddit_utils as utils
from filters import apply_filter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def build_post_content(
    post_data: Dict[str, Any],
    replies_data: List[Dict[str, Any]],
    settings: Any,  # If you have a Settings class, you could replace Any with "Settings"
    colors: List[str],
    url: str,
) -> str:
    """
    Builds the final Markdown for a post (including title, selftext, replies)
    and returns the rendered content as a single string.

    If the Settings object's 'file_format' is 'md', you receive standard Markdown.
    If it's 'html', a later step in your pipeline can convert this Markdown to HTML.

    :param post_data: A dictionary of primary post data (title, author, etc.)
    :param replies_data: A list of dictionaries containing top-level replies
    :param settings: A Settings-like object with user configurations (e.g., show_upvotes, filters, etc.)
    :param colors: A list of color symbols (strings) used to visually distinguish reply depths
    :param url: The post's original URL (used for reference if needed)
    :return: A single string containing Markdown (or near-Markdown) representing the post content
    """

    # Basic post info
    post_title = post_data.get("title", "Untitled")
    post_author = post_data.get("author", "[unknown]")
    subreddit = post_data.get("subreddit_name_prefixed", "")
    post_ups = post_data.get("ups", 0)
    post_locked = post_data.get("locked", False)
    post_selftext = post_data.get("selftext", "")
    post_url = post_data.get("url", "")
    created_utc = post_data.get("created_utc")

    # Format timestamp
    post_timestamp = ""
    if created_utc:
        dt = datetime.datetime.utcfromtimestamp(created_utc)
        post_timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

    # Upvotes
    upvotes_display = ""
    if settings.show_upvotes and post_ups is not None:
        upvotes_display = (
            f"⬆️ {int(post_ups/1000)}k" if post_ups >= 1000 else f"⬆️ {post_ups}"
        )

    timestamp_display = (
        f"_( {post_timestamp} )_"
        if (settings.show_timestamp and post_timestamp)
        else ""
    )

    # Locked?
    lock_msg = ""
    if post_locked:
        lock_msg = (
            f"---\n\n>🔒 **This thread has been locked by the moderators of {subreddit}**.\n"
            f"  New comments cannot be posted\n\n"
        )

    # Start building the content
    lines: List[str] = []
    lines.append(
        f"**{subreddit}** | Posted by u/{post_author} {upvotes_display} {timestamp_display}\n"
    )
    lines.append(f"## {post_title}\n")
    lines.append(f"Original post: [{post_url}]({post_url})\n")
    if lock_msg:
        lines.append(lock_msg)

    # Selftext
    if post_selftext:
        # Indent selftext lines with '>'
        selftext_escaped = (
            post_selftext.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
        )
        lines.append("> " + selftext_escaped.replace("\n", "\n> ") + "\n")

    # Count total replies (including deeper children)
    total_replies = len(replies_data)
    for rd in replies_data:
        replies_extras = utils.get_replies(rd, max_depth=settings.reply_depth_max)
        total_replies += len(replies_extras)

    lines.append(f"💬 ~ {total_replies} replies\n")
    lines.append("---\n\n")

    # Process top-level replies
    for reply_obj in replies_data:
        author = reply_obj.get("data", {}).get("author", "")
        if not author:
            continue
        if author == "AutoModerator" and not settings.show_auto_mod_comment:
            continue

        depth_color = colors[0] if settings.reply_depth_color_indicators else ""
        reply_ups = reply_obj.get("data", {}).get("ups", 0)
        upvote_str = ""
        if settings.show_upvotes and reply_ups is not None:
            upvote_str = (
                f"⬆️ {int(reply_ups/1000)}k" if reply_ups >= 1000 else f"⬆️ {reply_ups}"
            )

        created_utc = reply_obj.get("data", {}).get("created_utc", 0)
        top_reply_timestamp = ""
        if settings.show_timestamp and created_utc:
            dt = datetime.datetime.utcfromtimestamp(created_utc)
            top_reply_timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

        author_field = (
            f"[{author}](https://www.reddit.com/user/{author})"
            if author != "[deleted]"
            else author
        )
        if author == post_author:
            author_field += " (OP)"

        lines.append(
            f"* {depth_color} **{author_field}** {upvote_str} {f'_( {top_reply_timestamp} )_' if top_reply_timestamp else ''}\n\n"
        )

        body = reply_obj.get("data", {}).get("body", "")
        if not body.strip():
            continue

        # Render top-level reply body
        if body == "[deleted]":
            lines.append("\tComment deleted by user\n\n")
        else:
            filtered_text = apply_filter(
                author,
                body,
                reply_ups,
                settings.filtered_keywords,
                settings.filtered_authors,
                settings.filtered_min_upvotes,
                settings.filtered_regexes,
                settings.filtered_message,
            )
            formatted = (
                filtered_text.replace("&gt;", ">")
                .replace("\n", "\n\t")
                .replace("\r", "")
            )
            # Turn `u/username` into link
            formatted = re.sub(
                r"u/(\w+)", r"[u/\1](https://www.reddit.com/user/\1)", formatted
            )
            lines.append(f"\t{formatted}\n\n")

        # Gather child replies
        child_map = utils.get_replies(reply_obj, settings.reply_depth_max)
        for _, child_info in child_map.items():
            cdepth = child_info["depth"]
            child_reply = child_info["child_reply"].get("data", {})
            child_author = child_reply.get("author", "")
            child_ups = child_reply.get("ups", 0)
            child_body = child_reply.get("body", "")
            child_created_utc = child_reply.get("created_utc", 0)

            color_symbol = (
                colors[cdepth]
                if (settings.reply_depth_color_indicators and cdepth < len(colors))
                else ""
            )
            child_author_field = (
                f"[{child_author}](https://www.reddit.com/user/{child_author})"
                if child_author not in ("[deleted]", "")
                else child_author
            )
            if child_author == post_author and child_author_field:
                child_author_field += " (OP)"

            child_ups_str = ""
            if settings.show_upvotes and child_ups is not None:
                child_ups_str = (
                    f"⬆️ {int(child_ups/1000)}k"
                    if child_ups >= 1000
                    else f"⬆️ {child_ups}"
                )

            child_ts = ""
            if settings.show_timestamp and child_created_utc:
                dt = datetime.datetime.utcfromtimestamp(child_created_utc)
                child_ts = dt.strftime("%Y-%m-%d %H:%M:%S")

            indent = "\t" * cdepth
            lines.append(
                f"{indent}* {color_symbol} **{child_author_field}** {child_ups_str} {f'_( {child_ts} )_' if child_ts else ''}\n\n"
            )

            # Render child reply body
            if not child_body.strip():
                continue

            if child_body == "[deleted]":
                lines.append(f"{indent}\tComment deleted by user\n\n")
            else:
                filtered_child = apply_filter(
                    child_author,
                    child_body,
                    child_ups,
                    settings.filtered_keywords,
                    settings.filtered_authors,
                    settings.filtered_min_upvotes,
                    settings.filtered_regexes,
                    settings.filtered_message,
                )
                child_formatted = filtered_child.replace("&gt;", ">").replace(
                    "&amp;#32;", " "
                )
                # fix certain bot signature chars
                child_formatted = child_formatted.replace("^^[", "[").replace(
                    "^^(", "("
                )
                child_formatted = re.sub(
                    r"u/(\w+)",
                    r"[u/\1](https://www.reddit.com/user/\1)",
                    child_formatted,
                )
                child_formatted = child_formatted.replace("\n", f"\n{indent}\t")
                lines.append(f"{indent}\t{child_formatted}\n\n")

        if settings.line_break_between_parent_replies:
            lines.append("---\n\n")

    lines.append("\n")
    return "".join(lines)
