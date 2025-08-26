# Reddit Markdown - Rust Implementation

A Rust port of the Reddit Markdown tool that saves Reddit posts and their comments as Markdown or HTML files.

## Features

- Download Reddit posts and comments as Markdown or HTML
- Support for authentication with Reddit API
- Filter comments by keywords, authors, upvotes, and regex patterns
- Download media (images, videos, galleries) from posts
- Support for subreddit and multireddit batch processing
- Customizable output formatting and organization
- Command-line interface with multiple input options

## Prerequisites

- Rust 1.70 or higher
- Cargo (comes with Rust)

## Building

1. Navigate to the rust directory:
```bash
cd rust
```

2. Build the project:
```bash
cargo build --release
```

The compiled binary will be available at `target/release/reddit-markdown`

## Configuration

The tool uses the same `settings.json` file as the Python version, located in the parent directory (`../settings.json`).

Key configuration options:
- `file_format`: Output format ("md" for Markdown, "html" for HTML)
- `auth`: Reddit API credentials for authenticated requests
- `filters`: Content filtering rules
- `default_save_location`: Default directory for saving posts
- `enable_media_downloads`: Enable/disable media downloading

## Usage

### Basic Usage

```bash
# Run in demo mode
./target/release/reddit-markdown

# Process specific URLs
./target/release/reddit-markdown --urls "https://www.reddit.com/r/rust/comments/..."

# Process URLs from files
./target/release/reddit-markdown --src-files urls.txt,more_urls.csv

# Process entire subreddits
./target/release/reddit-markdown --subs r/rust,r/programming

# Process multireddits (defined in settings.json)
./target/release/reddit-markdown --multis m/programming
```

### Interactive Mode

When run without arguments, the tool enters interactive mode where you can:
- Enter Reddit post URLs directly
- Use `demo` for a demo post
- Use `surprise` for a random post from r/popular
- Use `r/subreddit` to fetch posts from a subreddit
- Use `m/multireddit` to fetch posts from a multireddit

### Environment Variables

- `DEFAULT_REDDIT_SAVE_LOCATION`: Default directory for saving posts
- `RUST_LOG`: Set logging level (e.g., `RUST_LOG=info`)

## Differences from Python Version

This Rust implementation maintains feature parity with the Python version while offering:
- Better performance and memory efficiency
- Type safety and compile-time error checking
- Native binary with no runtime dependencies
- Improved error handling with detailed error messages

## Development

To run in development mode with debug output:
```bash
RUST_LOG=debug cargo run
```

To run tests:
```bash
cargo test
```

To check code without building:
```bash
cargo check
```

## License

Same as the parent project - see LICENSE.txt in the root directory.