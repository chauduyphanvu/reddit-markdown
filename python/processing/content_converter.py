import re
import markdown
from typing import Optional
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class ContentConverter:
    @staticmethod
    def markdown_to_html(markdown_text: str) -> str:
        try:
            md = markdown.Markdown(
                extensions=[
                    "extra",
                    "codehilite",
                    "nl2br",
                    "toc",
                    "tables",
                    "fenced_code",
                ]
            )
            html_content = md.convert(markdown_text)

            html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reddit Post</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        blockquote {
            border-left: 4px solid #ccc;
            margin-left: 0;
            padding-left: 20px;
            color: #666;
        }
        pre {
            background-color: #f4f4f4;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 2px;
        }
        a {
            color: #0079d3;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        img, video {
            max-width: 100%;
            height: auto;
        }
        .comment {
            margin-left: 20px;
            padding-left: 10px;
            border-left: 2px solid #e0e0e0;
        }
        .deleted {
            color: #999;
            font-style: italic;
        }
    </style>
</head>
<body>
    {}
</body>
</html>"""
            return html_template.format(html_content)

        except ImportError:
            logger.warning(
                "markdown library not installed. Returning raw markdown wrapped in HTML."
            )
            return f"<html><body><pre>{markdown_text}</pre></body></html>"
        except Exception as e:
            logger.error("Error converting markdown to HTML: %s", e)
            return f"<html><body><pre>{markdown_text}</pre></body></html>"

    @staticmethod
    def clean_url(url: str) -> str:
        if not url:
            return url

        url = url.split("?utm_source")[0]
        url = url.split("?ref=")[0]
        url = url.split("?context=")[0]

        url = url.rstrip("/")

        return url

    @staticmethod
    def valid_url(url: str) -> bool:
        if not url:
            return False

        reddit_patterns = [
            r"https?://(?:www\.)?reddit\.com/r/[^/]+/comments/[a-z0-9]+/",
            r"https?://(?:www\.)?reddit\.com/[^/]+/comments/[a-z0-9]+/",
            r"https?://(?:old\.)?reddit\.com/r/[^/]+/comments/[a-z0-9]+/",
            r"https?://redd\.it/[a-z0-9]+",
        ]

        for pattern in reddit_patterns:
            if re.match(pattern, url):
                return True

        return False

    @staticmethod
    def escape_html_entities(text: str) -> str:
        return (
            text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&nbsp;", " ")
        )
