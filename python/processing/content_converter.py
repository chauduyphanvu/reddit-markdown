import re
import markdown
from typing import Optional
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class ContentConverter:
    @staticmethod
    def markdown_to_html(markdown_text: str) -> str:
        """Convert markdown text to HTML with proper extensions and styling.

        Uses industry-standard markdown extensions for comprehensive formatting:
        - extra: Abbreviations, attribute lists, definition lists, footnotes
        - codehilite: Syntax highlighting for code blocks
        - nl2br: Converts newlines to <br> tags
        - toc: Table of contents generation
        - tables: GitHub-flavored markdown tables
        - fenced_code: ```-style code blocks

        Args:
            markdown_text: Raw markdown content to convert

        Returns:
            Complete HTML document with embedded CSS styling
        """
        # Input validation
        if not markdown_text:
            logger.warning("Empty markdown input provided")
            return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Empty Content</title>
</head>
<body>
    <p><em>No content to display</em></p>
</body>
</html>"""

        if not isinstance(markdown_text, str):
            logger.error(
                "Invalid input type: expected string, got %s", type(markdown_text)
            )
            return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Invalid Input</title>
</head>
<body>
    <p style="color: red;">Error: Invalid input type</p>
</body>
</html>"""

        try:
            md = markdown.Markdown(
                extensions=[
                    "extra",
                    "codehilite",
                    "nl2br",
                    "toc",
                    "tables",
                    "fenced_code",
                    "sane_lists",  # Better list handling
                    "smarty",  # Smart quotes and typography
                ],
                extension_configs={
                    "codehilite": {
                        "css_class": "highlight",
                        "use_pygments": False,  # Use CSS classes instead
                    },
                    "toc": {
                        "permalink": True,
                        "permalink_title": "Link to this section",
                    },
                },
            )
            html_content = md.convert(markdown_text)

            html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reddit Post</title>
    <style>
        :root {
            --primary-color: #0079d3;
            --text-color: #1c1c1c;
            --bg-color: #ffffff;
            --secondary-bg: #f8f9fa;
            --border-color: #edeff1;
            --code-bg: #f6f8fa;
            --quote-border: #dfe2e5;
        }
        
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            max-width: 1000px;
            margin: 0 auto;
            padding: 2rem;
            background-color: var(--bg-color);
            font-size: 16px;
        }
        
        h1, h2, h3, h4, h5, h6 {
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            font-weight: 600;
            line-height: 1.25;
        }
        
        blockquote {
            border-left: 4px solid var(--quote-border);
            margin: 1rem 0;
            padding: 0.5rem 1rem;
            background-color: var(--secondary-bg);
            color: #6a737d;
            border-radius: 0 4px 4px 0;
        }
        
        pre {
            background-color: var(--code-bg);
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            font-size: 0.875rem;
            line-height: 1.45;
        }
        
        code {
            background-color: var(--code-bg);
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-size: 0.875em;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
        }
        
        pre code {
            background-color: transparent;
            padding: 0;
            border-radius: 0;
            font-size: inherit;
        }
        
        a {
            color: var(--primary-color);
            text-decoration: none;
            transition: color 0.2s ease;
        }
        
        a:hover {
            color: #0060a0;
            text-decoration: underline;
        }
        
        img, video {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }
        
        th, td {
            border: 1px solid var(--border-color);
            padding: 0.5rem 0.75rem;
            text-align: left;
        }
        
        th {
            background-color: var(--secondary-bg);
            font-weight: 600;
        }
        
        .toc {
            background-color: var(--secondary-bg);
            padding: 1rem;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            margin: 1rem 0;
        }
        
        .toc ul {
            margin: 0;
            padding-left: 1.5rem;
        }
        
        .comment {
            margin-left: 1.5rem;
            padding-left: 0.75rem;
            border-left: 2px solid var(--border-color);
        }
        
        .deleted {
            color: #999;
            font-style: italic;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            body {
                padding: 1rem;
                font-size: 14px;
            }
            
            .comment {
                margin-left: 1rem;
                padding-left: 0.5rem;
            }
        }
    </style>
</head>
<body>
    {}
</body>
</html>"""
            return html_template.replace("{}", html_content)

        except ImportError:
            logger.warning(
                "markdown library not installed. Install with: pip install markdown"
            )
            # Return a properly formatted HTML fallback
            escaped_text = markdown_text.replace("<", "&lt;").replace(">", "&gt;")
            return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reddit Post (Fallback)</title>
    <style>
        body {{ font-family: monospace; white-space: pre-wrap; padding: 20px; }}
    </style>
</head>
<body>{escaped_text}</body>
</html>"""
        except ValueError as e:
            logger.error("Markdown parsing error: %s", e)
            # Return HTML with the error message and original content
            escaped_text = markdown_text.replace("<", "&lt;").replace(">", "&gt;")
            return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Markdown Parse Error</title>
    <style>
        body {{ font-family: monospace; padding: 20px; }}
        .error {{ color: red; background: #fee; padding: 10px; margin-bottom: 20px; border: 1px solid #fcc; border-radius: 4px; }}
        .content {{ white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="error">Error parsing Markdown: {str(e)}</div>
    <div class="content">{escaped_text}</div>
</body>
</html>"""
        except Exception as e:
            logger.error("Unexpected error converting markdown to HTML: %s", e)
            # Return a safe fallback
            escaped_text = markdown_text.replace("<", "&lt;").replace(">", "&gt;")
            return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Content Display Error</title>
    <style>
        body {{ font-family: monospace; padding: 20px; white-space: pre-wrap; }}
        .error {{ color: red; background: #fee; padding: 10px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="error">Error processing content: {str(e)}</div>
    {escaped_text}
</body>
</html>"""

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
