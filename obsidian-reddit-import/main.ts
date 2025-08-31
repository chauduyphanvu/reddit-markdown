import {
	App,
	Editor,
	MarkdownView,
	Modal,
	Notice,
	Plugin,
	PluginSettingTab,
	Setting,
	TFile,
	TFolder,
	normalizePath,
	requestUrl,
	RequestUrlResponse
} from 'obsidian';

interface RedditImportSettings {
	redditClientId: string;
	redditClientSecret: string;
	saveLocation: string;
	organizationMethod: 'subreddit' | 'date' | 'flat';
	templatePath: string;
	defaultTemplate: string;
	autoCreateMOCs: boolean;
	autoLinkUsers: boolean;
	autoLinkSubreddits: boolean;
	autoLinkExistingNotes: boolean;
	maxCommentDepth: number;
	minUpvotesToInclude: number;
	includeAutoModComments: boolean;
	debugMode: boolean;
}

const DEFAULT_SETTINGS: RedditImportSettings = {
	redditClientId: '',
	redditClientSecret: '',
	saveLocation: 'Reddit',
	organizationMethod: 'subreddit',
	templatePath: '',
	defaultTemplate: `---
reddit_id: {{post_id}}
subreddit: "[[r/{{subreddit}}]]"
author: "[[u/{{author}}]]"
created: {{created_date}}
upvotes: {{upvotes}}
comment_count: {{comment_count}}
url: {{url}}
tags: [reddit{{#tags}}, {{.}}{{/tags}}]
---

# {{title}}

> Post by [[u/{{author}}]] in [[r/{{subreddit}}]]
> 🔗 [Original Thread]({{url}})
> ⬆️ {{upvotes}} upvotes | 💬 {{comment_count}} comments

## Post Content

{{content}}

## Comments

{{comments}}

---
*Imported: {{import_date}}*`,
	autoCreateMOCs: true,
	autoLinkUsers: true,
	autoLinkSubreddits: true,
	autoLinkExistingNotes: true,
	maxCommentDepth: 3,
	minUpvotesToInclude: 2,
	includeAutoModComments: false,
	debugMode: false
};

export default class RedditImportPlugin extends Plugin {
	settings: RedditImportSettings;
	redditClient: RedditClient;
	rateLimiter: RateLimiter;

	async onload() {
		await this.loadSettings();
		
		// Initialize components
		this.redditClient = new RedditClient(this.settings);
		this.rateLimiter = new RateLimiter();

		// Add ribbon icon
		this.addRibbonIcon('message-circle', 'Import Reddit Post', (evt: MouseEvent) => {
			new RedditImportModal(this.app, this).open();
		});

		// Add command: Import single Reddit URL
		this.addCommand({
			id: 'import-reddit-url',
			name: 'Import Reddit post from URL',
			callback: () => {
				new RedditImportModal(this.app, this).open();
			}
		});

		// Add command: Bulk import
		this.addCommand({
			id: 'import-reddit-bulk',
			name: 'Bulk import Reddit posts',
			callback: () => {
				new BulkImportModal(this.app, this).open();
			}
		});

		// Add command: Update existing Reddit posts
		this.addCommand({
			id: 'update-reddit-posts',
			name: 'Update existing Reddit posts',
			callback: async () => {
				await this.updateExistingPosts();
			}
		});

		// Add command: Create MOC for Reddit posts
		this.addCommand({
			id: 'create-reddit-moc',
			name: 'Create MOC for Reddit posts',
			callback: async () => {
				await this.createRedditMOC();
			}
		});

		// Add settings tab
		this.addSettingTab(new RedditImportSettingTab(this.app, this));

		// Register custom post processor for Reddit links
		this.registerMarkdownPostProcessor((element, context) => {
			const links = element.querySelectorAll('a');
			links.forEach(link => {
				const href = link.getAttribute('href');
				if (href && this.isRedditUrl(href)) {
					link.addClass('reddit-link');
					link.setAttribute('title', 'Click to import this Reddit post');
				}
			});
		});

		console.log('Reddit Import plugin loaded');
	}

	onunload() {
		console.log('Reddit Import plugin unloaded');
	}

	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}

	isRedditUrl(url: string): boolean {
		return /^https?:\/\/(www\.)?(reddit\.com|redd\.it)/.test(url);
	}

	async importRedditPost(url: string): Promise<TFile | null> {
		try {
			// Validate URL
			if (!this.isRedditUrl(url)) {
				new Notice('Invalid Reddit URL');
				return null;
			}

			// Parse Reddit URL
			const urlParser = new RedditUrlParser(url);
			const postInfo = urlParser.parse();
			
			if (!postInfo) {
				new Notice('Could not parse Reddit URL');
				return null;
			}

			// Check rate limit
			await this.rateLimiter.wait();

			// Fetch post data
			new Notice('Fetching Reddit post...');
			const postData = await this.redditClient.fetchPost(postInfo.postId);
			
			if (!postData) {
				new Notice('Failed to fetch Reddit post');
				return null;
			}

			// Format post content
			const formatter = new RedditFormatter(this.settings, this.app);
			const markdown = await formatter.formatPost(postData);

			// Determine save location
			const filePath = this.getFilePath(postData);

			// Ensure directory exists
			await this.ensureDirectoryExists(filePath);

			// Create or update file
			const file = await this.savePostToVault(filePath, markdown);

			// Auto-create MOC if enabled
			if (this.settings.autoCreateMOCs) {
				await this.updateMOC(postData, file);
			}

			new Notice(`✅ Imported: ${postData.title}`);
			return file;

		} catch (error) {
			console.error('Error importing Reddit post:', error);
			new Notice(`Failed to import post: ${error.message}`);
			return null;
		}
	}

	async updateExistingPosts() {
		const redditFiles = await this.getRedditFiles();
		let updated = 0;
		
		for (const file of redditFiles) {
			try {
				const metadata = this.app.metadataCache.getFileCache(file);
				if (metadata?.frontmatter?.reddit_id) {
					await this.rateLimiter.wait();
					const postData = await this.redditClient.fetchPost(metadata.frontmatter.reddit_id);
					
					if (postData) {
						const formatter = new RedditFormatter(this.settings, this.app);
						const markdown = await formatter.formatPost(postData);
						await this.app.vault.modify(file, markdown);
						updated++;
					}
				}
			} catch (error) {
				console.error(`Failed to update ${file.path}:`, error);
			}
		}
		
		new Notice(`Updated ${updated} Reddit posts`);
	}

	async createRedditMOC() {
		const redditFiles = await this.getRedditFiles();
		const moc = new MOCGenerator(this.app, this.settings);
		const mocContent = await moc.generate(redditFiles);
		
		const mocPath = normalizePath(`${this.settings.saveLocation}/MOCs/Reddit Posts MOC.md`);
		await this.ensureDirectoryExists(mocPath);
		
		const existingFile = this.app.vault.getAbstractFileByPath(mocPath);
		if (existingFile instanceof TFile) {
			await this.app.vault.modify(existingFile, mocContent);
		} else {
			await this.app.vault.create(mocPath, mocContent);
		}
		
		new Notice('Reddit MOC created/updated');
	}

	private getFilePath(postData: RedditPost): string {
		const date = new Date(postData.created_utc * 1000);
		const dateStr = date.toISOString().split('T')[0];
		const sanitizedTitle = postData.title
			.replace(/[\\/:*?"<>|]/g, '')
			.substring(0, 100);
		
		let path = this.settings.saveLocation;
		
		switch (this.settings.organizationMethod) {
			case 'subreddit':
				path = `${path}/r-${postData.subreddit}`;
				break;
			case 'date':
				path = `${path}/${dateStr}`;
				break;
		}
		
		return normalizePath(`${path}/${dateStr} - ${sanitizedTitle}.md`);
	}

	private async ensureDirectoryExists(filePath: string) {
		const dir = filePath.substring(0, filePath.lastIndexOf('/'));
		const folder = this.app.vault.getAbstractFileByPath(dir);
		
		if (!folder) {
			await this.app.vault.createFolder(dir);
		}
	}

	private async savePostToVault(filePath: string, content: string): Promise<TFile> {
		const existingFile = this.app.vault.getAbstractFileByPath(filePath);
		
		if (existingFile instanceof TFile) {
			await this.app.vault.modify(existingFile, content);
			return existingFile;
		} else {
			return await this.app.vault.create(filePath, content);
		}
	}

	private async getRedditFiles(): Promise<TFile[]> {
		const files = this.app.vault.getMarkdownFiles();
		return files.filter(file => {
			const cache = this.app.metadataCache.getFileCache(file);
			return cache?.frontmatter?.reddit_id;
		});
	}
}

// Reddit URL Parser
class RedditUrlParser {
	private url: string;

	constructor(url: string) {
		this.url = url.replace(/\?.*$/, ''); // Remove query parameters
	}

	parse(): { postId: string; subreddit?: string } | null {
		// Handle different Reddit URL formats
		const patterns = [
			/reddit\.com\/r\/(\w+)\/comments\/(\w+)/,
			/redd\.it\/(\w+)/,
			/reddit\.com\/(\w+)/ // Short links
		];

		for (const pattern of patterns) {
			const match = this.url.match(pattern);
			if (match) {
				if (match.length === 3) {
					return {
						subreddit: match[1],
						postId: match[2]
					};
				} else if (match.length === 2) {
					return {
						postId: match[1]
					};
				}
			}
		}

		return null;
	}
}

// Rate Limiter
class RateLimiter {
	private lastRequest: number = 0;
	private minInterval: number = 1000; // 1 request per second

	async wait() {
		const now = Date.now();
		const timeSinceLastRequest = now - this.lastRequest;
		
		if (timeSinceLastRequest < this.minInterval) {
			const waitTime = this.minInterval - timeSinceLastRequest;
			await this.sleep(waitTime);
		}
		
		this.lastRequest = Date.now();
	}

	private sleep(ms: number): Promise<void> {
		return new Promise(resolve => setTimeout(resolve, ms));
	}
}

// Reddit API Client
class RedditClient {
	private settings: RedditImportSettings;
	private accessToken: string | null = null;
	private tokenExpiry: number = 0;

	constructor(settings: RedditImportSettings) {
		this.settings = settings;
	}

	async fetchPost(postId: string): Promise<RedditPost | null> {
		try {
			// Get access token if needed
			if (this.settings.redditClientId && this.settings.redditClientSecret) {
				await this.ensureAccessToken();
			}

			// Fetch from Reddit API
			const url = `https://www.reddit.com/comments/${postId}.json`;
			const headers: Record<string, string> = {
				'User-Agent': 'Obsidian Reddit Import/1.0'
			};

			if (this.accessToken) {
				headers['Authorization'] = `Bearer ${this.accessToken}`;
			}

			const response = await requestUrl({
				url,
				headers,
				method: 'GET'
			});

			if (response.status !== 200) {
				throw new Error(`Reddit API returned status ${response.status}`);
			}

			const data = response.json;
			return this.parseRedditResponse(data);

		} catch (error) {
			console.error('Error fetching Reddit post:', error);
			return null;
		}
	}

	private async ensureAccessToken() {
		if (this.accessToken && Date.now() < this.tokenExpiry) {
			return;
		}

		const auth = btoa(`${this.settings.redditClientId}:${this.settings.redditClientSecret}`);
		
		try {
			const response = await requestUrl({
				url: 'https://www.reddit.com/api/v1/access_token',
				method: 'POST',
				headers: {
					'Authorization': `Basic ${auth}`,
					'Content-Type': 'application/x-www-form-urlencoded',
					'User-Agent': 'Obsidian Reddit Import/1.0'
				},
				body: 'grant_type=client_credentials'
			});

			if (response.json.access_token) {
				this.accessToken = response.json.access_token;
				this.tokenExpiry = Date.now() + (response.json.expires_in * 1000);
			}
		} catch (error) {
			console.error('Failed to get Reddit access token:', error);
		}
	}

	private parseRedditResponse(data: any): RedditPost | null {
		try {
			if (!Array.isArray(data) || data.length < 2) {
				return null;
			}

			const postData = data[0].data.children[0].data;
			const commentsData = data[1].data.children;

			return {
				id: postData.id,
				title: postData.title,
				author: postData.author,
				subreddit: postData.subreddit,
				created_utc: postData.created_utc,
				upvotes: postData.ups,
				url: `https://reddit.com${postData.permalink}`,
				selftext: postData.selftext || '',
				num_comments: postData.num_comments,
				comments: this.parseComments(commentsData)
			};
		} catch (error) {
			console.error('Error parsing Reddit response:', error);
			return null;
		}
	}

	private parseComments(comments: any[], depth: number = 0): RedditComment[] {
		const result: RedditComment[] = [];
		
		for (const comment of comments) {
			if (comment.kind === 't1' && comment.data) {
				const data = comment.data;
				
				const parsed: RedditComment = {
					id: data.id,
					author: data.author,
					body: data.body,
					upvotes: data.ups,
					created_utc: data.created_utc,
					depth,
					replies: []
				};

				if (data.replies && data.replies.data && data.replies.data.children) {
					parsed.replies = this.parseComments(data.replies.data.children, depth + 1);
				}

				result.push(parsed);
			}
		}
		
		return result;
	}
}

// Types
interface RedditPost {
	id: string;
	title: string;
	author: string;
	subreddit: string;
	created_utc: number;
	upvotes: number;
	url: string;
	selftext: string;
	num_comments: number;
	comments: RedditComment[];
}

interface RedditComment {
	id: string;
	author: string;
	body: string;
	upvotes: number;
	created_utc: number;
	depth: number;
	replies: RedditComment[];
}

// Reddit Content Formatter
class RedditFormatter {
	private settings: RedditImportSettings;
	private app: App;

	constructor(settings: RedditImportSettings, app: App) {
		this.settings = settings;
		this.app = app;
	}

	async formatPost(post: RedditPost): Promise<string> {
		const date = new Date(post.created_utc * 1000);
		const importDate = new Date();

		const templateVars = {
			post_id: post.id,
			title: post.title,
			author: post.author,
			subreddit: post.subreddit,
			created_date: date.toISOString().split('T')[0],
			upvotes: post.upvotes.toString(),
			comment_count: post.num_comments.toString(),
			url: post.url,
			content: this.formatContent(post.selftext),
			comments: this.formatComments(post.comments),
			import_date: importDate.toISOString().split('T')[0],
			tags: this.extractTags(post)
		};

		let content = this.settings.defaultTemplate;
		
		// Replace template variables
		for (const [key, value] of Object.entries(templateVars)) {
			if (Array.isArray(value)) {
				// Handle array values (tags)
				const tagSection = content.match(/\{\{#tags\}\}(.*?)\{\{\/tags\}\}/s);
				if (tagSection) {
					const tagTemplate = tagSection[1];
					const tagContent = value.map(tag => tagTemplate.replace('{{.}}', tag)).join('');
					content = content.replace(/\{\{#tags\}\}.*?\{\{\/tags\}\}/s, tagContent);
				}
			} else {
				content = content.replace(new RegExp(`{{${key}}}`, 'g'), value);
			}
		}

		// Apply auto-linking
		if (this.settings.autoLinkUsers) {
			content = this.autoLinkUsers(content);
		}
		if (this.settings.autoLinkSubreddits) {
			content = this.autoLinkSubreddits(content);
		}
		if (this.settings.autoLinkExistingNotes) {
			content = await this.autoLinkExistingNotes(content);
		}

		return content;
	}

	private formatContent(text: string): string {
		if (!text) return '*No text content*';
		
		// Convert Reddit markdown to Obsidian markdown
		return text
			.replace(/^&gt;/gm, '>') // Fix quotes
			.replace(/&amp;/g, '&')
			.replace(/&lt;/g, '<')
			.replace(/&gt;/g, '>')
			.replace(/&#x200B;/g, '') // Remove zero-width spaces
			.trim();
	}

	private formatComments(comments: RedditComment[], currentDepth: number = 0): string {
		if (currentDepth >= this.settings.maxCommentDepth) {
			return '';
		}

		const formatted: string[] = [];
		
		for (const comment of comments) {
			if (comment.upvotes < this.settings.minUpvotesToInclude) {
				continue;
			}
			
			if (!this.settings.includeAutoModComments && comment.author === 'AutoModerator') {
				continue;
			}

			const indent = '  '.repeat(comment.depth);
			const header = `${indent}### [[u/${comment.author}]] (${comment.upvotes} ⬆️)`;
			const body = this.formatContent(comment.body)
				.split('\n')
				.map(line => `${indent}${line}`)
				.join('\n');
			
			formatted.push(`${header}\n${body}`);
			
			if (comment.replies.length > 0) {
				const replies = this.formatComments(comment.replies, currentDepth + 1);
				if (replies) {
					formatted.push(replies);
				}
			}
		}
		
		return formatted.join('\n\n');
	}

	private autoLinkUsers(content: string): string {
		return content.replace(/(?<!\[)u\/(\w+)(?!\])/g, '[[u/$1]]');
	}

	private autoLinkSubreddits(content: string): string {
		return content.replace(/(?<!\[)r\/(\w+)(?!\])/g, '[[r/$1]]');
	}

	private async autoLinkExistingNotes(content: string): Promise<string> {
		const files = this.app.vault.getMarkdownFiles();
		const fileNames = new Set(files.map(f => f.basename));
		
		// Find potential note references
		const words = content.match(/\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g) || [];
		
		for (const word of words) {
			if (fileNames.has(word) && !content.includes(`[[${word}]]`)) {
				content = content.replace(new RegExp(`\\b${word}\\b`, 'g'), `[[${word}]]`);
			}
		}
		
		return content;
	}

	private extractTags(post: RedditPost): string[] {
		const tags: string[] = [];
		
		// Add subreddit as tag
		tags.push(`r-${post.subreddit}`);
		
		// Extract potential tags from title and content
		const text = `${post.title} ${post.selftext}`.toLowerCase();
		
		// Common tag patterns
		if (text.includes('question') || text.includes('?')) tags.push('question');
		if (text.includes('discussion')) tags.push('discussion');
		if (text.includes('help') || text.includes('advice')) tags.push('help');
		if (text.includes('guide') || text.includes('tutorial')) tags.push('tutorial');
		if (text.includes('news') || text.includes('announcement')) tags.push('news');
		
		return [...new Set(tags)];
	}
}

// MOC Generator
class MOCGenerator {
	private app: App;
	private settings: RedditImportSettings;

	constructor(app: App, settings: RedditImportSettings) {
		this.app = app;
		this.settings = settings;
	}

	async generate(files: TFile[]): Promise<string> {
		const subreddits = new Map<string, TFile[]>();
		const dates = new Map<string, TFile[]>();
		const tags = new Map<string, TFile[]>();
		
		for (const file of files) {
			const cache = this.app.metadataCache.getFileCache(file);
			const frontmatter = cache?.frontmatter;
			
			if (frontmatter) {
				// Group by subreddit
				if (frontmatter.subreddit) {
					const sub = frontmatter.subreddit.replace(/[\[\]]/g, '').replace('r/', '');
					if (!subreddits.has(sub)) subreddits.set(sub, []);
					subreddits.get(sub)!.push(file);
				}
				
				// Group by date
				if (frontmatter.created) {
					const month = frontmatter.created.substring(0, 7);
					if (!dates.has(month)) dates.set(month, []);
					dates.get(month)!.push(file);
				}
				
				// Group by tags
				if (frontmatter.tags) {
					for (const tag of frontmatter.tags) {
						if (!tags.has(tag)) tags.set(tag, []);
						tags.get(tag)!.push(file);
					}
				}
			}
		}
		
		let moc = '# Reddit Posts MOC\n\n';
		moc += `*Last updated: ${new Date().toISOString().split('T')[0]}*\n\n`;
		moc += `Total posts: **${files.length}**\n\n`;
		
		// By Subreddit
		moc += '## By Subreddit\n\n';
		for (const [sub, subFiles] of Array.from(subreddits.entries()).sort()) {
			moc += `### r/${sub} (${subFiles.length})\n`;
			for (const file of subFiles.slice(0, 10)) {
				moc += `- [[${file.basename}]]\n`;
			}
			if (subFiles.length > 10) {
				moc += `- *...and ${subFiles.length - 10} more*\n`;
			}
			moc += '\n';
		}
		
		// Recent Posts
		moc += '## Recent Posts\n\n';
		const recent = files
			.sort((a, b) => b.stat.mtime - a.stat.mtime)
			.slice(0, 20);
		for (const file of recent) {
			moc += `- [[${file.basename}]]\n`;
		}
		
		// By Tags
		moc += '\n## By Tags\n\n';
		for (const [tag, tagFiles] of Array.from(tags.entries()).sort()) {
			moc += `### #${tag} (${tagFiles.length})\n`;
			for (const file of tagFiles.slice(0, 5)) {
				moc += `- [[${file.basename}]]\n`;
			}
			if (tagFiles.length > 5) {
				moc += `- *...and ${tagFiles.length - 5} more*\n`;
			}
			moc += '\n';
		}
		
		return moc;
	}
}

// Import Modal
class RedditImportModal extends Modal {
	plugin: RedditImportPlugin;
	urlInput: HTMLInputElement;

	constructor(app: App, plugin: RedditImportPlugin) {
		super(app);
		this.plugin = plugin;
	}

	onOpen() {
		const { contentEl } = this;
		
		contentEl.createEl('h2', { text: 'Import Reddit Post' });
		
		const inputContainer = contentEl.createDiv('reddit-import-input-container');
		inputContainer.createEl('label', { text: 'Reddit URL:' });
		
		this.urlInput = inputContainer.createEl('input', {
			type: 'text',
			placeholder: 'https://reddit.com/r/...'
		});
		this.urlInput.addClass('reddit-import-input');
		
		// Check clipboard for Reddit URL
		navigator.clipboard.readText().then(text => {
			if (this.plugin.isRedditUrl(text)) {
				this.urlInput.value = text;
			}
		});
		
		const buttonContainer = contentEl.createDiv('reddit-import-buttons');
		
		const importButton = buttonContainer.createEl('button', { text: 'Import' });
		importButton.addClass('mod-cta');
		importButton.onclick = async () => {
			const url = this.urlInput.value.trim();
			if (url) {
				this.close();
				await this.plugin.importRedditPost(url);
			}
		};
		
		const cancelButton = buttonContainer.createEl('button', { text: 'Cancel' });
		cancelButton.onclick = () => this.close();
		
		// Allow Enter to submit
		this.urlInput.addEventListener('keypress', (e) => {
			if (e.key === 'Enter') {
				importButton.click();
			}
		});
		
		// Focus input
		this.urlInput.focus();
	}

	onClose() {
		const { contentEl } = this;
		contentEl.empty();
	}
}

// Bulk Import Modal
class BulkImportModal extends Modal {
	plugin: RedditImportPlugin;
	textArea: HTMLTextAreaElement;

	constructor(app: App, plugin: RedditImportPlugin) {
		super(app);
		this.plugin = plugin;
	}

	onOpen() {
		const { contentEl } = this;
		
		contentEl.createEl('h2', { text: 'Bulk Import Reddit Posts' });
		contentEl.createEl('p', { text: 'Enter Reddit URLs (one per line) or subreddit names (e.g., r/obsidian):' });
		
		this.textArea = contentEl.createEl('textarea', {
			placeholder: 'https://reddit.com/r/obsidian/comments/...\nr/obsidian\nr/productivity'
		});
		this.textArea.addClass('reddit-bulk-import-textarea');
		this.textArea.rows = 10;
		
		const optionsContainer = contentEl.createDiv('reddit-import-options');
		
		const limitContainer = optionsContainer.createDiv();
		limitContainer.createEl('label', { text: 'Max posts per subreddit: ' });
		const limitInput = limitContainer.createEl('input', {
			type: 'number',
			value: '10'
		});
		limitInput.addClass('reddit-import-limit-input');
		
		const buttonContainer = contentEl.createDiv('reddit-import-buttons');
		
		const importButton = buttonContainer.createEl('button', { text: 'Import All' });
		importButton.addClass('mod-cta');
		importButton.onclick = async () => {
			const lines = this.textArea.value.split('\n').filter(line => line.trim());
			const limit = parseInt(limitInput.value) || 10;
			
			this.close();
			
			let imported = 0;
			let failed = 0;
			
			for (const line of lines) {
				const trimmed = line.trim();
				
				if (trimmed.startsWith('r/')) {
					// Import top posts from subreddit
					const subreddit = trimmed.substring(2);
					new Notice(`Fetching top posts from r/${subreddit}...`);
					
					try {
						const urls = await this.fetchSubredditPosts(subreddit, limit);
						for (const url of urls) {
							const file = await this.plugin.importRedditPost(url);
							if (file) imported++;
							else failed++;
						}
					} catch (error) {
						console.error(`Failed to fetch r/${subreddit}:`, error);
						failed += limit;
					}
				} else if (this.plugin.isRedditUrl(trimmed)) {
					// Import specific URL
					const file = await this.plugin.importRedditPost(trimmed);
					if (file) imported++;
					else failed++;
				}
			}
			
			new Notice(`Bulk import complete: ${imported} imported, ${failed} failed`);
		};
		
		const cancelButton = buttonContainer.createEl('button', { text: 'Cancel' });
		cancelButton.onclick = () => this.close();
		
		this.textArea.focus();
	}

	async fetchSubredditPosts(subreddit: string, limit: number): Promise<string[]> {
		const response = await requestUrl({
			url: `https://www.reddit.com/r/${subreddit}/top.json?limit=${limit}&t=week`,
			headers: {
				'User-Agent': 'Obsidian Reddit Import/1.0'
			}
		});
		
		const urls: string[] = [];
		if (response.json?.data?.children) {
			for (const child of response.json.data.children) {
				if (child.data?.permalink) {
					urls.push(`https://reddit.com${child.data.permalink}`);
				}
			}
		}
		
		return urls;
	}

	onClose() {
		const { contentEl } = this;
		contentEl.empty();
	}
}

// Settings Tab
class RedditImportSettingTab extends PluginSettingTab {
	plugin: RedditImportPlugin;

	constructor(app: App, plugin: RedditImportPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		containerEl.createEl('h2', { text: 'Reddit Import Settings' });

		// Reddit API Settings
		containerEl.createEl('h3', { text: 'Reddit API (Optional)' });
		containerEl.createEl('p', { 
			text: 'Configure for higher rate limits. Get credentials at reddit.com/prefs/apps',
			cls: 'setting-item-description'
		});

		new Setting(containerEl)
			.setName('Reddit Client ID')
			.setDesc('Your Reddit app client ID')
			.addText(text => text
				.setPlaceholder('Enter client ID')
				.setValue(this.plugin.settings.redditClientId)
				.onChange(async (value) => {
					this.plugin.settings.redditClientId = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Reddit Client Secret')
			.setDesc('Your Reddit app client secret')
			.addText(text => {
				text.inputEl.type = 'password';
				text
					.setPlaceholder('Enter client secret')
					.setValue(this.plugin.settings.redditClientSecret)
					.onChange(async (value) => {
						this.plugin.settings.redditClientSecret = value;
						await this.plugin.saveSettings();
					});
			});

		// Organization Settings
		containerEl.createEl('h3', { text: 'Organization' });

		new Setting(containerEl)
			.setName('Save location')
			.setDesc('Folder where Reddit posts will be saved')
			.addText(text => text
				.setPlaceholder('Reddit')
				.setValue(this.plugin.settings.saveLocation)
				.onChange(async (value) => {
					this.plugin.settings.saveLocation = value || 'Reddit';
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Organization method')
			.setDesc('How to organize saved posts')
			.addDropdown(dropdown => dropdown
				.addOption('subreddit', 'By Subreddit')
				.addOption('date', 'By Date')
				.addOption('flat', 'Flat (no subfolders)')
				.setValue(this.plugin.settings.organizationMethod)
				.onChange(async (value: 'subreddit' | 'date' | 'flat') => {
					this.plugin.settings.organizationMethod = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Auto-create MOCs')
			.setDesc('Automatically update Map of Content files')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.autoCreateMOCs)
				.onChange(async (value) => {
					this.plugin.settings.autoCreateMOCs = value;
					await this.plugin.saveSettings();
				}));

		// Linking Settings
		containerEl.createEl('h3', { text: 'Auto-linking' });

		new Setting(containerEl)
			.setName('Auto-link users')
			.setDesc('Convert u/username to [[u/username]]')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.autoLinkUsers)
				.onChange(async (value) => {
					this.plugin.settings.autoLinkUsers = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Auto-link subreddits')
			.setDesc('Convert r/subreddit to [[r/subreddit]]')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.autoLinkSubreddits)
				.onChange(async (value) => {
					this.plugin.settings.autoLinkSubreddits = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Auto-link existing notes')
			.setDesc('Automatically link to existing notes in your vault')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.autoLinkExistingNotes)
				.onChange(async (value) => {
					this.plugin.settings.autoLinkExistingNotes = value;
					await this.plugin.saveSettings();
				}));

		// Content Filtering
		containerEl.createEl('h3', { text: 'Content Filtering' });

		new Setting(containerEl)
			.setName('Max comment depth')
			.setDesc('Maximum depth of comment threads to import')
			.addSlider(slider => slider
				.setLimits(1, 10, 1)
				.setValue(this.plugin.settings.maxCommentDepth)
				.setDynamicTooltip()
				.onChange(async (value) => {
					this.plugin.settings.maxCommentDepth = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Minimum upvotes')
			.setDesc('Only import comments with this many upvotes')
			.addSlider(slider => slider
				.setLimits(0, 100, 1)
				.setValue(this.plugin.settings.minUpvotesToInclude)
				.setDynamicTooltip()
				.onChange(async (value) => {
					this.plugin.settings.minUpvotesToInclude = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Include AutoMod comments')
			.setDesc('Include AutoModerator comments')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.includeAutoModComments)
				.onChange(async (value) => {
					this.plugin.settings.includeAutoModComments = value;
					await this.plugin.saveSettings();
				}));

		// Debug Settings
		containerEl.createEl('h3', { text: 'Advanced' });

		new Setting(containerEl)
			.setName('Debug mode')
			.setDesc('Enable debug logging to console')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.debugMode)
				.onChange(async (value) => {
					this.plugin.settings.debugMode = value;
					await this.plugin.saveSettings();
				}));
	}
}