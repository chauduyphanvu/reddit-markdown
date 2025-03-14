#!/usr/bin/env python3

import argparse
import csv
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class Settings:
    """
    Manages loading and validation of settings from settings.json.
    """

    def __init__(self, settings_file="settings.json"):
        if not os.path.isfile(settings_file):
            sys.exit(
                "❌Error: settings.json not found. Please provide a valid settings.json or download from GitHub."
            )
        self.raw = self._load_json(settings_file)
        if not self.raw:
            sys.exit("❌Error: settings.json appears to be empty or invalid.")
        self.version = self.raw.get("version", "0.0.0")
        self.file_format = self.raw.get("file_format", "md")
        self.update_check_on_startup = self.raw.get("update_check_on_startup", True)
        self.show_auto_mod_comment = self.raw.get("show_auto_mod_comment", True)
        self.line_break_between_parent_replies = self.raw.get(
            "line_break_between_parent_replies", True
        )
        self.show_upvotes = self.raw.get("show_upvotes", True)
        self.reply_depth_color_indicators = self.raw.get(
            "reply_depth_color_indicators", True
        )
        self.reply_depth_max = self.raw.get("reply_depth_max", -1)
        self.overwrite_existing_file = self.raw.get("overwrite_existing_file", False)
        self.save_posts_by_subreddits = self.raw.get("save_posts_by_subreddits", False)
        self.show_timestamp = self.raw.get("show_timestamp", True)
        self.use_timestamped_directories = self.raw.get(
            "use_timestamped_directories", False
        )
        self.filtered_message = self.raw.get("filtered_message", "Filtered")
        self.filtered_keywords = self.raw.get("filters", {}).get("keywords", [])
        self.filtered_min_upvotes = self.raw.get("filters", {}).get("min_upvotes", 0)
        self.filtered_authors = self.raw.get("filters", {}).get("authors", [])
        self.filtered_regexes = self.raw.get("filters", {}).get("regexes", [])
        self.default_save_location = self.raw.get("default_save_location", "")
        self.multi_reddits = self.raw.get("multi_reddits", {})

    def _load_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None

    def check_for_updates(self):
        """
        Optionally checks if a newer version is available on GitHub.
        We replicate the Ruby script’s approach with the GitHub Release endpoint.
        """
        check_url = (
            "https://api.github.com/repos/chauduyphanvu/reddit-markdown/releases"
        )
        try:
            req = urllib.request.Request(
                check_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            if not data:
                print(
                    "Warning: Could not fetch release info from GitHub. Please check manually."
                )
                return
            latest_tag = data[0].get("tag_name", "0.0.0")
            if re.match(r"\d+\.\d+\.\d+", latest_tag):
                from distutils.version import LooseVersion

                if LooseVersion(latest_tag) > LooseVersion(self.version):
                    print(
                        f"\nSuggestion: A new version ({latest_tag}) is available. You have {self.version}."
                    )
                    print(
                        "Download the latest version from https://github.com/chauduyphanvu/reddit-markdown."
                    )
            else:
                print("Warning: GitHub returned an invalid version number.")
        except Exception as e:
            print(f"❌Error: Could not check for updates: {e}")


class CommandLineArgs:
    """
    Parses command line arguments in a manner similar to the Ruby script.
    """

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Save the content (body and replies) of a Reddit post to Markdown or HTML."
        )
        self.parser.add_argument(
            "--urls",
            type=str,
            default="",
            help="Comma-separated list of Reddit post URLs.",
        )
        self.parser.add_argument(
            "--src-files",
            type=str,
            default="",
            help="Comma-separated list of file paths containing URLs.",
        )
        self.parser.add_argument(
            "--subs",
            type=str,
            default="",
            help='Comma-separated list of subreddits (e.g., "r/python,r/askreddit").',
        )
        self.parser.add_argument(
            "--multis",
            type=str,
            default="",
            help='Comma-separated list of multireddits (e.g., "m/programming").',
        )

        self.args = self.parser.parse_args()
        self.urls = self._parse_csv(self.args.urls)
        self.src_files = self._parse_csv(self.args.src_files)
        self.subs = self._parse_csv(self.args.subs)
        self.multis = self._parse_csv(self.args.multis)

    def _parse_csv(self, csv_str):
        if not csv_str:
            return []
        return [item.strip() for item in csv_str.split(",") if item.strip()]


class UrlFetcher:
    """
    Converts subreddits / multireddits / local files to an actual set of Reddit post URLs.
    If no arguments are given, it will prompt the user for input (similar to the Ruby script).
    """

    BASE_URL = "https://www.reddit.com"

    def __init__(self, settings, cli_args):
        self.settings = settings
        self.cli_args = cli_args
        self.urls = []
        # Convert CLI arguments to actual post links
        self._collect_urls()

        if not self.urls:
            # If no arguments provided, ask the user for input
            self._prompt_for_input()

    def _collect_urls(self):
        # 1) Direct URLs
        self.urls.extend(self.cli_args.urls)

        # 2) URLs from source files
        for file_path in self.cli_args.src_files:
            self.urls.extend(self._urls_from_file(file_path))

        # 3) Subreddit mode
        for subreddit in self.cli_args.subs:
            self.urls.extend(self._get_subreddit_posts(subreddit))

        # 4) Multireddit
        for multi_name in self.cli_args.multis:
            sub_list = self.settings.multi_reddits.get(multi_name, [])
            if not sub_list:
                print(
                    f"Warning: No subreddits found for {multi_name} in settings.json."
                )
            else:
                for sub in sub_list:
                    self.urls.extend(self._get_subreddit_posts(sub))

    def _urls_from_file(self, file_path):
        result = []
        if not os.path.isfile(file_path):
            print(f"Error: file '{file_path}' not found.")
            return result
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    # Each row can contain multiple comma-separated URLs
                    for url in row:
                        if url.strip():
                            result.append(url.strip())
        except Exception as e:
            print(f"Error reading file '{file_path}': {e}")
        return result

    def _prompt_for_input(self):
        print(
            "✏️ Enter/paste the Reddit link(s), comma-separated. Or 'demo', 'surprise', 'r/subreddit', or 'm/multireddit':"
        )
        user_in = input().strip()
        while not user_in:
            print("❌Error: No input provided. Try again.")
            user_in = input().strip()

        self.urls = self._interpret_input_mode(user_in)

    def _interpret_input_mode(self, user_in):
        if user_in.lower() == "demo":
            print("🔃Demo mode enabled.")
            return [
                "https://www.reddit.com/r/pcmasterrace/comments/101kjyq/my_dad_has_been_playing_civilization_almost_daily/"
            ]
        elif user_in.lower() == "surprise":
            print("🔃Surprise mode enabled. Grabbing one random post from r/popular.")
            return self._fetch_posts_from_sub("r/popular", pick_random=True)
        elif user_in.startswith("r/"):
            print(f"🔃Subreddit mode: fetching best posts from {user_in}...")
            return self._get_subreddit_posts(user_in, best=True)
        elif user_in.startswith("m/"):
            print(
                f"🔃Multireddit mode: attempting to fetch subreddits from settings for {user_in}..."
            )
            subs = self.settings.multi_reddits.get(user_in, [])
            results = []
            for s in subs:
                results.extend(self._get_subreddit_posts(s, best=True))
            return results
        else:
            # Just a direct link or multiple links
            return [x.strip() for x in user_in.split(",") if x.strip()]

    def _get_subreddit_posts(self, subreddit_str, best=True):
        """
        Fetch multiple posts from a given subreddit.
        If best=True, it uses /best.
        Otherwise, picks a single random post from all posts (like 'surprise' mode).
        """
        return self._fetch_posts_from_sub(subreddit_str, pick_random=False, best=best)

    def _fetch_posts_from_sub(self, subreddit_str, pick_random=False, best=False):
        subreddit_str = subreddit_str.lstrip("/")  # remove leading slash if present
        url = f"{self.BASE_URL}/{subreddit_str}"
        if best:
            url += "/best"
        json_data = self._download_post_json(url)
        if not json_data or "data" not in json_data:
            print(f"❌Error: Unable to fetch data from {url}.")
            return []
        children = json_data["data"].get("children", [])
        post_links = []
        for child in children:
            permalink = child["data"].get("permalink")
            if permalink:
                post_links.append(self.BASE_URL + permalink)
        if pick_random and post_links:
            import random

            return [random.choice(post_links)]
        return post_links

    def _download_post_json(self, url):
        """
        Helper that tries to fetch JSON from a subreddit listing or post URL (with `.json`).
        """
        json_url = url if url.endswith(".json") else url + ".json"
        try:
            req = urllib.request.Request(
                json_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"❌Error: Failed to download JSON data for {url}: {e}")
            return None
        except Exception as e:
            print(f"❌Error: Unexpected error while fetching {url}: {e}")
            return None


def clean_url(url):
    return url.strip().split("?utm_source")[0]


def valid_url(url):
    return bool(
        re.match(r"^https:\/\/www\.reddit\.com\/r\/\w+\/comments\/\w+\/[\w_]+\/?", url)
    )


def download_post_json(url):
    """
    Add `.json` to a Reddit post URL and fetch the post data.
    """
    json_url = url if url.endswith(".json") else url + ".json"
    req = urllib.request.Request(json_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"❌Error: could not download JSON for {url}. Reason: {e}")
        return None


def get_replies(reply_data, max_depth=-1):
    """
    Recursively gather child replies from a given reply’s "replies" field.
    """
    collected = {}
    replies_obj = reply_data.get("data", {}).get("replies")
    if not replies_obj:
        return collected

    children = replies_obj.get("data", {}).get("children", [])
    for child in children:
        child_id = child.get("data", {}).get("id")
        child_depth = child.get("data", {}).get("depth", 0)
        child_body = child.get("data", {}).get("body", "")

        # Stop if max depth exceeded (unless -1, i.e. no limit)
        if max_depth != -1 and child_depth > max_depth:
            continue
        if not child_body.strip():
            # skip empty/spam
            continue

        collected[child_id] = {"depth": child_depth, "child_reply": child}
        # Merge recursively
        collected.update(get_replies(child, max_depth))
    return collected


def apply_filter(
    author,
    text,
    upvotes,
    filtered_keywords,
    filtered_authors,
    min_upvotes,
    filtered_regexes,
    filtered_message,
):
    """
    Applies user-defined filters to a reply. If it matches any filter, returns `filtered_message`.
    """
    # keywords
    for kw in filtered_keywords:
        if kw.lower() in text.lower():
            return filtered_message
    # authors
    if author in filtered_authors:
        return filtered_message
    # upvotes
    if upvotes < min_upvotes:
        return filtered_message
    # regex
    for rgx in filtered_regexes:
        pattern = re.compile(rgx)
        if pattern.search(text):
            return filtered_message
    return text


def resolve_save_dir(config_directory):
    """
    If settings.json expects an environment variable for default location,
    handle that, otherwise prompt for location if empty.
    """
    if config_directory == "DEFAULT_REDDIT_SAVE_LOCATION":
        directory = os.environ.get("DEFAULT_REDDIT_SAVE_LOCATION", "")
        if not directory:
            sys.exit(
                "❌Error: DEFAULT_REDDIT_SAVE_LOCATION environment variable not set. Exiting..."
            )
        return directory
    elif config_directory:
        # Directory is set in config, use it directly if valid
        return config_directory
    else:
        # Ask user for directory
        print(
            f"=> Enter the full path to save the post(s). Hit Enter for current dir ({os.getcwd()})"
        )
        directory = input().strip()
        if not directory:
            directory = os.getcwd()
        while not os.path.isdir(directory):
            print("❌Error: Invalid path. Try again.")
            directory = input().strip()
            if not directory:
                directory = os.getcwd()
        return directory


def ensure_dir_exists(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def generate_filename(
    base_dir,
    url,
    subreddit,
    use_timestamped_dirs,
    post_timestamp,
    file_format,
    overwrite,
):
    """
    Generates a unique path for the output file, possibly placing it inside
    a subreddit folder and/or a timestamped folder, as configured.
    """
    # final base for the file
    name_candidate = url.rstrip("/").split("/")[-1]
    if not name_candidate:
        name_candidate = f"reddit_no_name_{int(time.time())}"

    if subreddit.startswith("r/"):
        subreddit = subreddit[2:]  # drop "r/"
    # Format the timestamp for a subdirectory
    dt_str = ""
    if post_timestamp:
        try:
            # post_timestamp is "YYYY-MM-DD HH:MM:SS"
            dt = datetime.datetime.strptime(post_timestamp, "%Y-%m-%d %H:%M:%S")
            dt_str = dt.strftime("%Y-%m-%d")
        except ValueError:
            dt_str = datetime.datetime.now().strftime("%Y-%m-%d")

    subdir = base_dir
    if subreddit:
        # We place inside subreddit dir
        subdir = os.path.join(subdir, subreddit)
    if use_timestamped_dirs and dt_str:
        subdir = os.path.join(subdir, dt_str)
    ensure_dir_exists(subdir)

    ext = file_format if file_format.lower() == "html" else "md"
    file_candidate = os.path.join(subdir, f"{name_candidate}.{ext}")
    if os.path.isfile(file_candidate):
        if overwrite:
            print(f"⚠️ Overwriting existing file: {os.path.basename(file_candidate)}")
            return file_candidate
        else:
            # find the next available suffix
            base_no_ext = os.path.splitext(file_candidate)[0]
            suffix = 1
            while os.path.isfile(f"{base_no_ext}_{suffix}.{ext}"):
                suffix += 1
            new_file = f"{base_no_ext}_{suffix}.{ext}"
            print(f"ℹ️ File exists. Using: {os.path.basename(new_file)}")
            return new_file
    return file_candidate


def markdown_to_html(md_content):
    """
    Convert Markdown to HTML.
    For simplicity, we’ll just do a quick conversion or (if you prefer) rely on Python’s `markdown` lib.
    Here, we'll do a minimal Kramdown-like transform with a basic library check or a fallback.
    """
    try:
        import markdown

        return markdown.markdown(md_content)
    except ImportError:
        # Minimal fallback: wrap in <pre>
        return f"<html><body><pre>{md_content}</pre></body></html>"


def main():
    # 1. Load settings
    settings = Settings()
    if settings.update_check_on_startup:
        settings.check_for_updates()

    # 2. Parse CLI args
    cli_args = CommandLineArgs()

    # 3. Fetch input URLs
    fetcher = UrlFetcher(settings, cli_args)
    all_urls = [clean_url(u) for u in fetcher.urls if u]

    # 4. Prepare save directory
    base_save_dir = resolve_save_dir(settings.default_save_location)

    # 5. Process each post URL
    colors = ["🟩", "🟨", "🟧", "🟦", "🟪", "🟥", "🟫", "⬛️", "⬜️"]
    for i, url in enumerate(all_urls, 1):
        if not valid_url(url):
            print(f"❌Error: Invalid post URL '{url}'. Skipping...")
            continue
        print(f"🔃Processing post {i} of {len(all_urls)}: {url}\n")

        data = download_post_json(url)
        if not data or len(data) < 2:
            print(f"❌Error: Could not fetch or parse post data for {url}. Skipping...")
            continue

        # The post (index 0)
        post_info = data[0].get("data", {}).get("children", [])
        if not post_info:
            print(f"❌Error: No post info found for {url}. Skipping...")
            continue
        post_data = post_info[0].get("data", {})
        post_title = post_data.get("title", "Untitled")
        post_author = post_data.get("author", "[unknown]")
        subreddit = post_data.get("subreddit_name_prefixed", "")
        post_ups = post_data.get("ups", 0)
        post_locked = post_data.get("locked", False)
        post_selftext = post_data.get("selftext", "")
        post_url = post_data.get("url", "")
        created_utc = post_data.get("created_utc")
        post_timestamp = ""
        if created_utc:
            dt = datetime.datetime.utcfromtimestamp(created_utc)
            post_timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

        # The replies (index 1)
        replies_data = data[1].get("data", {}).get("children", [])

        upvotes_display = ""
        if settings.show_upvotes and post_ups is not None:
            upvotes_display = (
                f"⬆️ {int(post_ups/1000)}k" if post_ups >= 1000 else f"⬆️ {post_ups}"
            )

        timestamp_display = (
            f"_( {post_timestamp} )_"
            if settings.show_timestamp and post_timestamp
            else ""
        )

        lock_msg = ""
        if post_locked:
            lock_msg = f"---\n\n>🔒 **This thread has been locked by the moderators of {subreddit}**.\n  New comments cannot be posted\n\n"

        # Start building the content
        lines = []
        lines.append(
            f"**{subreddit}** | Posted by u/{post_author} {upvotes_display} {timestamp_display}\n"
        )
        lines.append(f"## {post_title}\n")
        lines.append(f"Original post: [{post_url}]({post_url})\n")
        if lock_msg:
            lines.append(lock_msg)
        if post_selftext:
            # Indent selftext lines with '>'
            # Also convert HTML escapes if needed
            selftext_escaped = (
                post_selftext.replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&quot;", '"')
            )
            # We can do additional replacements as needed:
            lines.append("> " + selftext_escaped.replace("\n", "\n> ") + "\n")

        # Count total replies to show approximate
        total_replies = len(replies_data)
        for rd in replies_data:
            replies_extras = get_replies(rd, max_depth=settings.reply_depth_max)
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

            # Build the text snippet for the top-level reply
            depth_color = colors[0] if settings.reply_depth_color_indicators else ""
            reply_ups = reply_obj.get("data", {}).get("ups", 0)
            upvote_str = ""
            if settings.show_upvotes and reply_ups is not None:
                upvote_str = (
                    f"⬆️ {int(reply_ups/1000)}k"
                    if reply_ups >= 1000
                    else f"⬆️ {reply_ups}"
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

            if body == "[deleted]":
                lines.append("\tComment deleted by user\n\n")
            else:
                # Filter
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
                # Format newlines
                formatted = (
                    filtered_text.replace("&gt;", ">")
                    .replace("\n", "\n\t")
                    .replace("\r", "")
                )
                # Turn u/username into link
                formatted = re.sub(
                    r"u/(\w+)", r"[u/\1](https://www.reddit.com/user/\1)", formatted
                )
                lines.append(f"\t{formatted}\n\n")

            # Gather child replies
            child_map = get_replies(reply_obj, settings.reply_depth_max)
            for _, child_info in child_map.items():
                cdepth = child_info["depth"]
                child_author = (
                    child_info["child_reply"].get("data", {}).get("author", "")
                )
                child_ups = child_info["child_reply"].get("data", {}).get("ups", 0)
                child_body = child_info["child_reply"].get("data", {}).get("body", "")
                child_created_utc = (
                    child_info["child_reply"].get("data", {}).get("created_utc", 0)
                )

                color_symbol = (
                    colors[cdepth]
                    if settings.reply_depth_color_indicators and cdepth < len(colors)
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

                if not child_body.strip():
                    continue

                if child_body == "[deleted]":
                    lines.append(f"{indent}\tComment deleted by user\n\n")
                else:
                    # Filter child content
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
                    # format the child body
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
                    # indent newlines
                    child_formatted = child_formatted.replace("\n", f"\n{indent}\t")
                    lines.append(f"{indent}\t{child_formatted}\n\n")

            if settings.line_break_between_parent_replies:
                lines.append("---\n\n")

        lines.append("\n")

        # 6. Convert to HTML if required
        final_content = "".join(lines)
        if settings.file_format.lower() == "html":
            final_content = markdown_to_html(final_content)

        # 7. Save file
        target_path = generate_filename(
            base_save_dir,
            url,
            subreddit,
            settings.use_timestamped_directories,
            post_timestamp,
            settings.file_format,
            settings.overwrite_existing_file,
        )
        print(f"🔃Saving post to {target_path}...\n")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        print(f"✅Reddit post saved at {target_path}.\n---\n")

    print("Thanks for using this script!\nIf you have issues, open an issue on GitHub:")
    print("https://github.com/chauduyphanvu/reddit-markdown/issues")


if __name__ == "__main__":
    main()
