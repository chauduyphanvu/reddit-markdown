# Reddit Import for Obsidian

Import Reddit posts and comments directly into your Obsidian vault with intelligent linking, organization, and formatting.

## Features

### Core Features
- 🔗 **One-click import** from Reddit URLs
- 📁 **Smart organization** by subreddit, date, or flat structure
- 🔄 **Auto-linking** of users, subreddits, and existing notes
- 📊 **Bulk import** from multiple URLs or entire subreddits
- 🗺️ **Auto-generated MOCs** (Maps of Content)
- 🔄 **Update tracking** for existing imported posts
- 🎨 **Customizable templates** for imported content
- 🔍 **Intelligent tagging** based on content analysis

### Auto-Linking System
- **Users**: `u/username` → `[[u/username]]`
- **Subreddits**: `r/subreddit` → `[[r/subreddit]]`
- **Existing notes**: Automatically detects and links to notes in your vault
- **Cross-references**: Builds connections between related discussions

### Organization Options
- **By Subreddit**: `Reddit/r-obsidian/post-title.md`
- **By Date**: `Reddit/2024-08-31/post-title.md`
- **Flat**: `Reddit/post-title.md`

## Installation

### From Obsidian Community Plugins (Coming Soon)
1. Open Settings → Community Plugins
2. Search for "Reddit Import"
3. Install and enable

### Manual Installation
1. Download the latest release from [GitHub Releases](https://github.com/chauduyphanvu/reddit-markdown/releases)
2. Extract files to `.obsidian/plugins/reddit-import/`
3. Reload Obsidian
4. Enable "Reddit Import" in Settings → Community Plugins

### Development Setup
```bash
# Clone the repository
git clone https://github.com/chauduyphanvu/reddit-markdown.git
cd reddit-markdown/obsidian-reddit-import

# Install dependencies
npm install

# Build the plugin
npm run build

# For development with auto-reload
npm run dev
```

## Usage

### Quick Start
1. **Copy a Reddit URL** to your clipboard
2. **Open Command Palette** (Cmd/Ctrl + P)
3. **Run "Import Reddit post from URL"**
4. **Paste URL** (auto-filled from clipboard)
5. **Click Import**

### Command Palette Commands

#### Import Reddit post from URL
Import a single Reddit post by providing its URL.

#### Bulk import Reddit posts
Import multiple posts at once:
```
https://reddit.com/r/obsidian/comments/abc123
https://reddit.com/r/productivity/comments/def456
r/obsidian
r/MachineLearning
```

#### Update existing Reddit posts
Refresh all previously imported Reddit posts with latest comments and scores.

#### Create MOC for Reddit posts
Generate or update a Map of Content organizing all your Reddit posts.

### Bulk Import from Subreddits
When you enter `r/subredditname` in bulk import, the plugin will:
1. Fetch the top posts from that subreddit (weekly top by default)
2. Import each post with full comments
3. Organize according to your settings
4. Auto-generate MOCs if enabled

### Smart Features

#### Content Detection & Tagging
The plugin automatically detects and tags:
- Questions (`question`)
- Discussions (`discussion`)
- Help/Advice posts (`help`)
- Tutorials/Guides (`tutorial`)
- News/Announcements (`news`)
- Subreddit-specific tags (`r-obsidian`)

#### Template Variables
Customize your import template with these variables:
- `{{post_id}}` - Reddit post ID
- `{{title}}` - Post title
- `{{author}}` - Post author
- `{{subreddit}}` - Subreddit name
- `{{created_date}}` - Post creation date
- `{{upvotes}}` - Upvote count
- `{{comment_count}}` - Number of comments
- `{{url}}` - Original Reddit URL
- `{{content}}` - Post content
- `{{comments}}` - Formatted comments
- `{{import_date}}` - Import date
- `{{#tags}}{{.}}{{/tags}}` - Auto-generated tags

## Configuration

### Reddit API (Optional)
For higher rate limits and better performance:

1. Go to [reddit.com/prefs/apps](https://reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Fill in:
   - Name: `Obsidian Reddit Import`
   - Type: `script`
   - Redirect URI: `http://localhost:8080`
4. Copy your Client ID and Client Secret
5. Add them in plugin settings

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Save location** | Folder for imported posts | `Reddit` |
| **Organization method** | How to organize posts | `By Subreddit` |
| **Auto-create MOCs** | Update MOCs on import | `Enabled` |
| **Auto-link users** | Convert u/username to links | `Enabled` |
| **Auto-link subreddits** | Convert r/subreddit to links | `Enabled` |
| **Auto-link existing notes** | Link to existing vault notes | `Enabled` |
| **Max comment depth** | Depth of comment threads | `3` |
| **Minimum upvotes** | Filter low-score comments | `2` |
| **Include AutoMod** | Include AutoModerator comments | `Disabled` |

## File Organization

### Default Structure
```
Vault/
├── Reddit/
│   ├── r-obsidian/
│   │   ├── 2024-08-31 - Plugin Development Question.md
│   │   └── 2024-08-30 - Weekly Theme Thread.md
│   ├── r-productivity/
│   │   └── 2024-08-31 - GTD vs PARA Discussion.md
│   ├── MOCs/
│   │   ├── Reddit Posts MOC.md
│   │   └── Reddit - Obsidian Discussions.md
│   └── Users/
│       ├── u-helpful_user.md
│       └── u-expert_contributor.md
```

### MOC Structure
MOCs are automatically generated with:
- Posts grouped by subreddit
- Recent posts list
- Tag-based organization
- Statistics and summaries
- Chronological grouping

## Use Cases

### Research & Academic
- Archive discussions for citations
- Track evolving conversations
- Build knowledge bases from community wisdom
- Cross-reference related discussions

### Content Creation
- Save inspiration and ideas
- Track community feedback
- Archive your own posts and discussions
- Monitor trending topics

### Personal Knowledge Management
- Integrate Reddit knowledge into your second brain
- Connect community discussions with personal notes
- Build topic-specific archives
- Track learning resources

## Advanced Features

### Custom Templates
Create custom templates in your vault and reference them in settings:
```markdown
---
type: reddit-post
source: {{url}}
archived: {{import_date}}
---

# {{title}}

*From r/{{subreddit}} by u/{{author}}*

{{content}}

## Key Insights
- 

## Related Notes
- [[]]
```

### Workflow Integration
- **Daily Notes**: Link imported posts to daily notes
- **Tags**: Use Obsidian's tag system for organization
- **Graph View**: Visualize connections between posts and topics
- **Search**: Full-text search across all imported content

## Troubleshooting

### Common Issues

**Rate Limiting**
- Configure Reddit API credentials for higher limits
- The plugin automatically handles rate limiting with delays

**Import Failures**
- Check the Reddit URL is valid and accessible
- Ensure the post hasn't been deleted
- Check console for error messages (if debug mode enabled)

**Missing Comments**
- Adjust "Minimum upvotes" setting
- Increase "Max comment depth" setting
- Check if AutoMod comments are filtered

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development
- Written in TypeScript
- Uses Obsidian Plugin API
- Follows Obsidian plugin best practices
- Comprehensive error handling

## Privacy & Security

- **No tracking**: The plugin doesn't collect any user data
- **Local storage**: All data stays in your vault
- **Optional API**: Reddit API credentials are optional and stored locally
- **No external services**: Direct connection to Reddit only

## Roadmap

- [ ] Real-time monitoring for post updates
- [ ] Media content preservation (images, videos)
- [ ] Comment threading improvements
- [ ] Export to other formats
- [ ] Saved posts import from Reddit account
- [ ] Custom filtering rules
- [ ] Scheduled imports
- [ ] Multi-vault sync

## Support

- **Issues**: [GitHub Issues](https://github.com/chauduyphanvu/reddit-markdown/issues)
- **Discussions**: [GitHub Discussions](https://github.com/chauduyphanvu/reddit-markdown/discussions)
- **Updates**: Watch the repository for updates

## License

MIT License - See [LICENSE](LICENSE) for details

## Credits

Created by [chauduyphanvu](https://github.com/chauduyphanvu) and the Reddit-Markdown community.

Special thanks to the Obsidian community for feedback and suggestions.

---

**Made with ❤️ for the Obsidian community**