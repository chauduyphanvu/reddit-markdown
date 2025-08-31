# Reddit to Markdown Converter

**Save Reddit posts as beautiful Markdown files for offline reading and research**

Ever found an amazing Reddit discussion that you want to save forever? Or maybe you're doing research and need to archive Reddit posts and comments? This tool downloads Reddit posts and converts them into clean, readable Markdown files that you can view in any text editor, note-taking app, or documentation tool.

**NEW!** ✨ **Automated Scheduling, Content Search & Standalone Archive Tool** - Set up the tool to automatically download posts from your favorite subreddits on any schedule (daily, weekly, hourly, etc.) with smart duplicate detection and persistent history tracking. Plus, full-text search and tag-based organization to find and organize your archived content! Includes a standalone high-performance archive compression tool for easy sharing and storage.

<div>
	<img src="https://chauduyphanvu.s3.us-east-2.amazonaws.com/screenshots/Reddit_Markdown_Raw.png" width="49%" />
	<img src="https://chauduyphanvu.s3.us-east-2.amazonaws.com/screenshots/Reddit_Markdown_Rendered.png" width="49%" />
</div>

## 🚀 Quick Start (Beginner-Friendly)

**Perfect for:** Students, researchers, data scientists, or anyone who wants to save Reddit content without technical complexity.

### What You'll Need
- A computer (Windows, Mac, or Linux)
- 5 minutes to set up
- No coding experience required!

### Step 1: Install Python
Python is a programming language that powers this tool. Don't worry - you won't need to write any code!

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.6 or newer (the website will recommend the best version for your computer)
3. Run the installer and follow the prompts
4. ✅ **Test it worked:** Open your terminal/command prompt and type `python3 --version`. You should see something like "Python 3.x.x"

### Step 2: Download This Tool
1. Go to the [latest release page](https://github.com/chauduyphanvu/reddit-markdown/releases)
2. Click "Source code (zip)" to download
3. Unzip the file to a folder you'll remember (like your Desktop or Documents)

### Step 3: Install Dependencies
These are helper libraries the tool needs to work with Reddit.

1. Open your terminal/command prompt
2. Navigate to the folder where you unzipped the tool
3. Run this command: `pip3 install -r requirements.txt`

### Step 4: Run the Tool
1. In your terminal, type: `python3 python/main.py`
2. The tool will ask you for:
   - **Reddit post URL(s)**: Copy and paste the link from your browser (like `https://www.reddit.com/r/askreddit/comments/abc123/`)
   - **Where to save**: Press Enter to save in the current folder, or type a path like `/Users/yourname/Documents/reddit-posts/`
3. Wait for the magic to happen! ✨

### Special Input Options

Instead of URLs, you can try these fun options:

- `demo` - Downloads a sample post to test the tool
- `surprise` - Gets a random popular post
- `r/subredditname` - Downloads trending posts from a specific subreddit (e.g., `r/science`)

### What You'll Get

After running the tool, you'll have beautiful Markdown files containing:
- The original post title and content
- All comments and replies (organized by reply depth)
- Upvote counts and timestamps
- Clean formatting that's easy to read

You can open these files in any text editor, import them into note-taking apps like Obsidian or Notion, or just read them as-is!

### 📦 Want to Compress Your Archives?

After downloading posts, you can use the **standalone archive tool** to compress them into efficient archives for sharing or backup:

```bash
# Compress your downloaded posts into an archive
python3 python/cli_archive.py create /path/to/your/downloaded/posts
```

### 🕐 Want It Automatic & Searchable?

Once you're comfortable with the basic tool, you can set up **automated scheduling** to download posts regularly without any manual work, plus use the **content search & indexing** feature to find and organize your archived content. Perfect for research, staying updated with communities, or building personal archives. See the [Automated Scheduling](#-automated-scheduling-new) and [Content Search & Indexing](#-content-search--indexing-new) sections below!

---

## ⚙️ Advanced Mode

**Perfect for:** Power users, developers, researchers doing bulk operations, or anyone wanting to customize the experience.

### Authentication (Recommended for Heavy Use)

If you plan to download many posts, set up Reddit authentication to avoid rate limits:

1. **Create a Reddit App:**
   - Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
   - Click "create an app"
   - Name: `reddit-markdown` (or anything you like)
   - Type: `script`
   - Redirect URI: `http://localhost:8080` (required but unused)

2. **Configure authentication:**
   - Copy the `.env.template` file to `.env`:
     ```bash
     cp .env.template .env
     ```
   - Open `.env` in a text editor
   - Replace the placeholder values with your app's credentials:
     ```
     REDDIT_CLIENT_ID=your_client_id_here
     REDDIT_CLIENT_SECRET=your_client_secret_here
     ```
   - In `settings.json`, set `"login_on_startup": true` in the auth section
   - **Important:** Never share your `.env` file - it contains your credentials!

### Command Line Arguments

Skip the interactive prompts and run everything from the command line:

```bash
# Download specific posts
python3 python/main.py --urls "https://reddit.com/r/science/comments/abc123,https://reddit.com/r/askreddit/comments/def456"

# Download trending posts from subreddits
python3 python/main.py --subs "r/MachineLearning,r/datascience,r/Python"

# Download from multireddit collections (see settings.json)
python3 python/main.py --multis "m/tech,m/science"

# Load URLs from files
python3 python/main.py --src-files "my-urls.txt,more-urls.csv"

# Load URLs from files
python3 python/main.py --src-files "my-urls.txt,more-urls.csv"
```

### Customization Options

Edit `settings.json` to control behavior:

| Setting | What It Does | Example Values |
|---------|-------------|----------------|
| `file_format` | Output format | `"md"` or `"html"` |
| `reply_depth_max` | How deep to save comment threads | `3` (saves 3 levels deep), `-1` (all levels) |
| `show_upvotes` | Include upvote counts | `true` or `false` |
| `save_posts_by_subreddits` | Organize files by subreddit folders | `true` or `false` |
| `default_save_location` | Where to save files | `"/Users/yourname/reddit-archive"` |
| `use_timestamped_directories` | Organize by date | `true` or `false` |
| `show_timestamp` | Include post timestamps | `true` or `false` |
| `overwrite_existing_file` | Overwrite existing files | `true` or `false` |

### 📦 Archive Compression (NEW!)

**Perfect for:** Sharing downloaded content, backup storage, or managing large collections efficiently.

The Reddit-Markdown tool now includes a **standalone archive tool** for high-performance compression of your downloaded content. This tool operates independently from the download process - first download your content, then use the archive tool to compress it for sharing, backup, and storage optimization.

#### Key Features

- **🚀 ZSTD Compression:** Ultra-fast compression with superior ratios (3x faster than traditional formats)
- **📦 ZIP Compatibility:** Universal ZIP format for maximum compatibility
- **⚡ Auto-Detection:** Automatically chooses the optimal compression format for your system
- **📊 Progress Tracking:** Real-time progress updates for large archive operations
- **🔧 Metadata Inclusion:** Detailed archive metadata with file information and timestamps
- **✅ Integrity Verification:** Built-in archive integrity checking and verification
- **🎯 Directory-Based:** Archive any directory containing downloaded Reddit content
- **🔐 Security:** Built-in protection against malicious file paths and unsafe operations

#### Standalone Archive Tool Usage

The archive tool is a separate command-line utility that works on existing downloaded content:

```bash
# Basic archive creation (auto-detects optimal format)
python3 python/cli_archive.py create /path/to/your/reddit-posts

# Specify compression format and level
python3 python/cli_archive.py create /path/to/reddit-posts --format zstd --level 5

# Maximum compression for storage optimization
python3 python/cli_archive.py create /path/to/reddit-posts --format zip --level 9

# Custom archive output path
python3 python/cli_archive.py create /path/to/reddit-posts --output /backups/reddit-archive-2024.zst

# Quiet mode (no progress output)
python3 python/cli_archive.py create /path/to/reddit-posts --quiet
```

#### Archive Management Commands

```bash
# Display archive information
python3 python/cli_archive.py info /path/to/archive.zip
python3 python/cli_archive.py info /path/to/archive.zst --detailed

# Verify archive integrity
python3 python/cli_archive.py verify /path/to/archive.zip

# List supported compression formats
python3 python/cli_archive.py formats
```

#### Archive Formats & Performance

| Format | Speed | Compression | Compatibility | Best For |
|--------|-------|-------------|---------------|----------|
| **ZSTD** (preferred) | ⚡⚡⚡ Ultra Fast | 🗜️🗜️ Excellent | Modern systems | Large archives, frequent use |
| **ZIP** (fallback) | ⚡⚡ Fast | 🗜️ Good | Universal | Sharing, older systems |

#### Installation for Optimal Performance

For best compression performance, install ZSTD support:

```bash
pip3 install zstandard
```

*If ZSTD is not available, the tool automatically falls back to ZIP compression.*

#### Workflow Integration

1. **Download content** using the main tool:
   ```bash
   python3 python/main.py --subs "r/MachineLearning,r/Python"
   ```

2. **Archive the downloaded content**:
   ```bash
   python3 python/cli_archive.py create /path/to/downloaded/posts
   ```

#### Archive Contents

Each archive includes:
- All downloaded markdown/HTML files with original directory structure
- Archive metadata (JSON file with creation info, file list, compression details)
- Preserved timestamps and file attributes
- Nested directory structures maintained

### Filtering Options

Control which comments get saved:

```json
"filters": {
  "keywords": ["spam", "deleted"],
  "min_upvotes": 5,
  "authors": ["AutoModerator"],
  "regexes": ["^\\[removed\\]$"]
}
```

### 🔍 Content Search & Indexing (NEW!)

**Perfect for:** Researchers, students, data scientists, or anyone building large Reddit archives who needs to quickly find specific content.

The Reddit-Markdown tool now includes a powerful search system that indexes all your downloaded posts and provides fast full-text search, tag-based organization, and smart filtering capabilities!

#### Quick Start with Search

1. **Index your existing posts:**
   ```bash
   # Index all posts in your archive
   python3 python/cli_search.py index /path/to/your/reddit-posts

   # Index specific directory with progress tracking
   python3 python/cli_search.py index /Users/name/reddit-archive --recursive
   ```

2. **Search your content:**
   ```bash
   # Simple text search
   python3 python/cli_search.py search "machine learning python"

   # Advanced search with filters
   python3 python/cli_search.py search "tutorial" --subreddit r/Python --min-upvotes 50 --limit 20

   # Search by author or date range
   python3 python/cli_search.py search --author python_guru --date-from 2024-01-01
   ```

3. **Organize with tags:**
   ```bash
   # Create custom tags
   python3 python/cli_search.py tag create "favorites" --description "My favorite posts" --color "#FF0000"

   # Tag posts manually
   python3 python/cli_search.py tag apply abc123def456 "favorites,tutorial,python"

   # Auto-tag based on content patterns
   python3 python/cli_search.py tag auto-apply abc123def456

   # Search by tags
   python3 python/cli_search.py search --tags "favorites,python"
   ```

#### Search Features

- **⚡ Full-Text Search:** Powered by SQLite FTS5 for lightning-fast searches across titles, content, and metadata
- **🏷️ Smart Tagging:** Manual tags plus automatic tagging based on content patterns (questions, tutorials, news, etc.)
- **🎯 Advanced Filtering:** Filter by subreddit, author, upvotes, date ranges, tags, and more
- **📊 Relevance Ranking:** Results ranked by BM25 algorithm for best match first
- **🔄 Incremental Indexing:** Only processes new or changed files for efficient updates
- **💾 Metadata Extraction:** Automatically extracts and indexes all Reddit post metadata

#### Search Configuration

Enable search features in `settings.json`:

```json
{
  "search": {
    "enabled": true,
    "database_path": "reddit_search.db",
    "auto_index_on_download": true,
    "auto_tag_posts": true,
    "max_indexer_threads": 4
  }
}
```

#### Example Search Scenarios

```bash
# Research workflow
python3 python/cli_search.py search "neural networks" --subreddit r/MachineLearning,r/deeplearning --min-upvotes 100

# Find your saved favorites
python3 python/cli_search.py search --tags favorites --sort upvotes --limit 50

# Track discussions by specific users
python3 python/cli_search.py search --author expert_username --date-from 2024-06-01

# Find tutorial content
python3 python/cli_search.py search --tags tutorial,guide --subreddit r/Python,r/learnpython

# Browse recent high-quality content
python3 python/cli_search.py search --min-upvotes 500 --date-from 2024-08-01 --sort date
```

#### Tag System

The search system includes a flexible tagging system with:

- **Manual Tags:** Create custom tags for your organization system
- **Auto Tags:** Automatically applied based on content patterns:
  - `question` - Posts with question words or question marks
  - `discussion` - Discussion and opinion-seeking posts
  - `tutorial` - How-to guides and tutorials
  - `news` - News and announcement posts
  - `review` - Product or service reviews
  - `sub_[subreddit]` - Automatic subreddit-based tags

### 🕐 Automated Scheduling (NEW!)

**Perfect for:** Regular content archiving, research data collection, keeping up with specific communities.

The Reddit-Markdown tool now includes a built-in scheduler that can automatically download posts from your favorite subreddits on a customizable schedule - no external cron jobs or GitHub Actions needed!

#### Quick Start with Scheduling

1. **Enable the scheduler** in `settings.json`:
   ```json
   {
     "scheduler": {
       "enabled": true
     }
   }
   ```

2. **Add a scheduled task using the CLI:**
   ```bash
   # Add a new scheduled task to download Python posts daily at 9 AM
   python3 python/scheduler_cli.py add "Daily Python Posts" "0 9 * * *" "r/python,r/learnpython" --max-posts 15

   # Start the scheduler daemon to run tasks
   python3 python/scheduler_cli.py start
   ```

3. **Or define tasks in settings.json:**
   ```json
   {
     "scheduler": {
       "enabled": true,
       "scheduled_tasks": [
         {
           "name": "Morning Tech News",
           "cron_expression": "0 9 * * *",
           "subreddits": ["r/programming", "r/technology"],
           "max_posts_per_subreddit": 10
         },
         {
           "name": "Weekly ML Papers",
           "cron_expression": "0 10 * * 1",
           "subreddits": ["r/MachineLearning", "r/deeplearning"],
           "max_posts_per_subreddit": 20
         }
       ]
     }
   }
   ```

#### Schedule Examples

The scheduler uses standard cron expressions plus friendly shortcuts:

| Expression | When It Runs | Use Case |
|------------|--------------|----------|
| `@daily` or `0 0 * * *` | Every day at midnight | Daily news roundup |
| `0 9 * * *` | Every day at 9 AM | Morning reading material |
| `0 */6 * * *` | Every 6 hours | High-activity subreddits |
| `0 10 * * 1` | Mondays at 10 AM | Weekly digest |
| `*/30 * * * *` | Every 30 minutes | Breaking news or trending topics |
| `@weekly` | Sundays at midnight | Weekly summary |

#### Command Line Interface

Manage your scheduled tasks with a full CLI:

```bash
# Task Management
python3 python/scheduler_cli.py add "Task Name" "0 12 * * *" "r/subreddit1,r/subreddit2"
python3 python/scheduler_cli.py list                   # Show all tasks
python3 python/scheduler_cli.py show TASK_ID           # Task details
python3 python/scheduler_cli.py enable TASK_ID         # Enable a task
python3 python/scheduler_cli.py disable TASK_ID        # Disable a task
python3 python/scheduler_cli.py remove TASK_ID         # Delete a task

# Scheduler Control
python3 python/scheduler_cli.py start                  # Start scheduler daemon
python3 python/scheduler_cli.py status                 # Show status
python3 python/scheduler_cli.py stats                  # Detailed statistics

# History and Analysis
python3 python/scheduler_cli.py history --limit 50            # Recent downloads
python3 python/scheduler_cli.py history --subreddit r/python  # Subreddit-specific

# Utilities
python3 python/scheduler_cli.py validate "0 9 * * *"   # Test cron expressions
python3 python/scheduler_cli.py test TASK_ID           # Test task execution
```

#### Advanced Scheduling Configuration

Full control through `settings.json`:

```json
{
  "scheduler": {
    "enabled": true,
    "check_interval_seconds": 30,
    "database_path": "scheduler_state.db",
    "cleanup_old_history_days": 90,
    "default_max_posts_per_subreddit": 25,
    "default_retry_count": 3,
    "default_retry_delay_seconds": 60,
    "default_timeout_seconds": 3600
  }
}
```

#### Smart Features

- **🔍 Duplicate Detection:** Never downloads the same post twice
- **📊 Download History:** Track what's been downloaded and when
- **🛡️ Error Recovery:** Tasks continue running even if individual posts fail
- **⚡ Rate Limiting:** Respects Reddit API limits automatically
- **💾 Persistent State:** Survives computer restarts and crashes
- **📈 Statistics:** Detailed analytics on your download activity
- **🧹 Auto Cleanup:** Automatically removes old download records

#### Integration with Existing Workflow

The scheduler works seamlessly alongside manual downloads:
- Uses the same settings, filters, and output formats
- Integrates with your existing authentication setup
- Saves files to the same locations using your naming preferences
- Respects all your filtering rules (keywords, upvotes, etc.)

#### External Automation (Alternative)

If you prefer external scheduling tools, here's a sample GitHub Actions workflow:

```yaml
name: Archive Reddit Posts
on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM

jobs:
  archive:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - run: |
        pip3 install -r requirements.txt
        python3 python/main.py --subs "r/MachineLearning,r/datascience"
```

### File Organization

Enable timestamped directories to organize posts by date:

```
your-save-folder/
├── MachineLearning/
│   ├── 2024-08-30/
│   │   ├── awesome-ml-paper-discussion.md
│   │   └── career-advice-thread.md
│   └── 2024-08-29/
│       └── dataset-sharing-thread.md
└── datascience/
    └── 2024-08-30/
        └── pandas-vs-polars-debate.md
```

---

## 💡 Why Use This Tool?

- **🔍 Research-Friendly:** Perfect for academic research, sentiment analysis, or data collection
- **📱 Offline Access:** Read Reddit content anywhere, anytime
- **🎨 Clean Format:** No ads, no distractions, just content
- **🔎 Searchable:** Use your computer's search to find specific discussions
- **💾 Backup:** Preserve valuable discussions that might get deleted
- **🔒 Privacy:** No tracking, no data collection - everything stays on your computer
- **🕐 Automated:** NEW! Set up schedules to automatically download posts from your favorite subreddits
- **📊 Smart Filtering:** Avoid duplicates and filter content by keywords, upvotes, or regex patterns
- **🔍 Full-Text Search:** NEW! Lightning-fast search and tag-based organization of your archived content
- **📦 Standalone Archive Tool:** NEW! High-performance ZSTD/ZIP compression tool for efficient storage and sharing
- **⚡ Scalable:** From single posts to bulk archiving thousands of discussions

## 🛠️ Technical Details

- **Languages:** Python (primary), Ruby (legacy)
- **Output Formats:** Markdown, HTML
- **Cross-Platform:** Works on Windows, Mac, Linux
- **Search Engine:** SQLite FTS5 full-text search with BM25 ranking
- **Scheduling:** Built-in cron-like scheduler with SQLite persistence
- **Standalone Archive Tool:** ZSTD (ultra-fast) and ZIP (universal) support with integrity verification
- **Well-Tested:** Comprehensive test suite with 5000+ lines of test code
- **Robust:** Thread-safe, error recovery, rate limiting, duplicate detection
- **Open Source:** Free forever, contribute on GitHub
- **Python-Native CI/CD:** Modern automated testing, quality checks, and release management

---

## 👩‍💻 For Contributors & Developers

### Local Development & CI/CD

This project uses a **Python-native CI/CD system** that you can run locally:

```bash
# Navigate to the python directory
cd python

# Run the full CI pipeline locally (same as GitHub Actions)
python3 ci                    # Full CI pipeline
python3 ci --list             # List available commands
python3 ci --help             # Show detailed help

# Run specific checks
python3 ci test              # Tests only
python3 ci quality           # Code quality
python3 ci security          # Security scans
```

### Available Pipelines
- **`ci`** - Full validation (tests + quality + security)
- **`quick`** - Fast feedback (tests only)
- **`quality`** - Code quality analysis
- **`security`** - Security scanning
- **`release`** - Release management
- **`dependencies`** - Dependency updates

### Testing
```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test categories
python3 -m pytest tests/test_main.py -v             # Main application tests
python3 -m pytest tests/test_integration.py -v      # Integration tests
python3 -m pytest tests/test_search_*.py -v         # Search system tests
python3 -m pytest tests/test_archive_*.py -v        # Archive system tests
```

---

## 🚨 Important Notes

- Only saves publicly visible comments (Reddit hides some low-score comments)
- Respects Reddit's rate limits (authentication helps with heavy usage)
- Desktop only (though you could run it remotely)
- This is a personal project - community contributions welcome!

## 📚 Need Help?

- 🐛 **Found a bug?** [Open an issue on GitHub](https://github.com/chauduyphanvu/reddit-markdown/issues)
- 💡 **Have a suggestion?** Pull requests are welcome!
- ❓ **Need support?** Check the issues page for common problems and solutions

---

**Happy archiving!** 🎉 Now you can save all those amazing Reddit discussions and never worry about losing them again.
