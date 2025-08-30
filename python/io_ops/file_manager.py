import os
import re
import datetime
from pathlib import Path
from typing import Optional, Tuple
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class FileManager:
    @staticmethod
    def ensure_dir_exists(directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def write_to_file(file_path: Path, content: str) -> None:
        FileManager.ensure_dir_exists(file_path.parent)
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def generate_filename(
        base_dir: str,
        url: str,
        subreddit: str = "",
        use_timestamped_dirs: bool = True,
        post_timestamp: str = "",
        file_format: str = "md",
        overwrite: bool = False,
    ) -> str:
        post_id = FileManager._extract_post_id(url)

        Path(base_dir).mkdir(parents=True, exist_ok=True)

        if use_timestamped_dirs and post_timestamp:
            dt = datetime.datetime.strptime(post_timestamp, "%Y-%m-%d %H:%M:%S")
            year_month = dt.strftime("%Y_%m")
            sub_dir = os.path.join(base_dir, year_month)
            Path(sub_dir).mkdir(parents=True, exist_ok=True)
            base_dir = sub_dir

        safe_name = FileManager._get_safe_filename(
            f"{subreddit}_{post_id}" if subreddit else post_id
        )
        extension = "html" if file_format.lower() == "html" else "md"
        filename = f"{safe_name}.{extension}"

        full_path = os.path.join(base_dir, filename)

        if not overwrite and os.path.exists(full_path):
            counter = 1
            while os.path.exists(full_path):
                filename = f"{safe_name}_{counter}.{extension}"
                full_path = os.path.join(base_dir, filename)
                counter += 1

        return full_path

    @staticmethod
    def _extract_post_id(url: str) -> str:
        match = re.search(r"/comments/([a-z0-9]+)/", url)
        if match:
            return match.group(1)

        parts = url.rstrip("/").split("/")
        for part in reversed(parts):
            if part and part not in ["comments", "r", "www.reddit.com", "reddit.com"]:
                return part

        return "unknown_post"

    @staticmethod
    def _get_safe_filename(name: str, max_length: int = 255) -> str:
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        name = re.sub(r"\.+$", "", name)
        name = name.strip()

        if len(name) > max_length:
            name = name[:max_length]

        return name or "unnamed"

    @staticmethod
    def resolve_save_dir(default_location: str) -> str:
        if default_location:
            expanded = os.path.expanduser(default_location)
            if os.path.isabs(expanded):
                save_dir = expanded
            else:
                save_dir = os.path.join(os.getcwd(), expanded)
        else:
            save_dir = os.path.join(os.getcwd(), "reddit_posts")

        Path(save_dir).mkdir(parents=True, exist_ok=True)
        return save_dir
