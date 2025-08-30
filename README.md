# Reddit to Markdown Converter

**Save Reddit posts as beautiful Markdown files for offline reading and research**

Ever found an amazing Reddit discussion that you want to save forever? Or maybe you're doing research and need to archive Reddit posts and comments? This tool downloads Reddit posts and converts them into clean, readable Markdown files that you can view in any text editor, note-taking app, or documentation tool.

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

### Automation

Run the tool automatically using GitHub Actions, cron jobs, or task schedulers. Here's a sample GitHub Actions workflow:

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

- **Research-Friendly:** Perfect for academic research, sentiment analysis, or data collection
- **Offline Access:** Read Reddit content anywhere, anytime
- **Clean Format:** No ads, no distractions, just content
- **Searchable:** Use your computer's search to find specific discussions
- **Backup:** Preserve valuable discussions that might get deleted
- **Privacy:** No tracking, no data collection - everything stays on your computer

## 🛠️ Technical Details

- **Languages:** Python (primary), Ruby (legacy)
- **Output Formats:** Markdown, HTML
- **Cross-Platform:** Works on Windows, Mac, Linux
- **Well-Tested:** Comprehensive test suite with 5000+ lines of test code
- **Open Source:** Free forever, contribute on GitHub

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