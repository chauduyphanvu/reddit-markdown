import { App, Modal, Notice, Plugin, PluginSettingTab, Setting, request } from 'obsidian';

interface RedditMarkdownSettings {
	redditApiUrl: string;
	saveLocation: string;
	useTimestampedDirectories: boolean;
	fileFormat: 'markdown' | 'html';
	overwriteExistingFile: boolean;
	loginOnStartup: boolean;
	clientId: string;
	clientSecret: string;
	lastUpdateCheck: number;
	updateCheckOnStartup: boolean;
}

const DEFAULT_SETTINGS: RedditMarkdownSettings = {
	redditApiUrl: 'https://www.reddit.com',
	saveLocation: '',
	useTimestampedDirectories: false,
	fileFormat: 'markdown',
	overwriteExistingFile: false,
	loginOnStartup: false,
	clientId: '',
	clientSecret: '',
	updateCheckOnStartup: true,
	lastUpdateCheck: 0
}

export default class RedditMarkdownPlugin extends Plugin {
	settings: RedditMarkdownSettings;
	accessToken: string;

	async onload() {
		await this.loadSettings();

		this.addCommand({
			id: 'fetch-reddit-post',
			name: 'Fetch Reddit Post',
			callback: () => {
				new RedditUrlModal(this.app, (url) => {
					this.fetchAndSavePost(url);
				}).open();
			}
		});

		this.addSettingTab(new RedditMarkdownSettingTab(this.app, this));

		if (this.settings.loginOnStartup) {
			await this.login();
		}

		if (this.settings.updateCheckOnStartup) {
			await this.checkForUpdates();
		}
	}

	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}

	async login() {
		if (!this.settings.clientId || !this.settings.clientSecret) {
			new Notice('Client ID and Client Secret must be set to log in.');
			return;
		}

		const response = await request({
			url: 'https://www.reddit.com/api/v1/access_token',
			method: 'POST',
			headers: {
				'Authorization': `Basic ${btoa(`${this.settings.clientId}:${this.settings.clientSecret}`)}`,
				'Content-Type': 'application/x-www-form-urlencoded'
			},
			body: 'grant_type=client_credentials'
		});

		const data = JSON.parse(response);
		this.accessToken = data.access_token;

		if (this.accessToken) {
			new Notice('Successfully logged in to Reddit.');
		} else {
			new Notice('Failed to log in to Reddit.');
		}
	}

	async checkForUpdates() {
		const now = new Date().getTime();
		// Check for updates every 24 hours
		if (now - this.settings.lastUpdateCheck < 24 * 60 * 60 * 1000) {
			return;
		}

		this.settings.lastUpdateCheck = now;
		await this.saveSettings();

		try {
			const response = await request({
				url: 'https://api.github.com/repos/chauduyphanvu/reddit-markdown/releases/latest',
			});
			const data = JSON.parse(response);
			const latestVersion = data.tag_name;
			const currentVersion = this.manifest.version;

			if (latestVersion > currentVersion) {
				new Notice(`A new version of Reddit Markdown is available: ${latestVersion}. Please update the plugin.`);
			}
		} catch (error) {
			console.error('Error checking for updates:', error);
		}
	}

	async fetchAndSavePost(url: string) {
		try {
			new Notice(`Fetching post from: ${url}`);

			const postUrl = `${this.settings.redditApiUrl}${new URL(url).pathname}.json`;
			const headers: Record<string, string> = {};
			if (this.accessToken) {
				headers['Authorization'] = `Bearer ${this.accessToken}`;
			}
			const response = await request({ url: postUrl, headers });
			const data = JSON.parse(response);

			const post = data[0].data.children[0].data;
			const comments = data[1].data.children;

			let markdown = `# ${post.title}\n\n`;
			markdown += `**Author:** /u/${post.author}\n`;
			markdown += `**Subreddit:** ${post.subreddit_name_prefixed}\n`;
			markdown += `**Score:** ${post.score}\n`;
			markdown += `**URL:** ${post.url}\n\n`;
			markdown += `---\n\n`;
			markdown += `${post.selftext}\n\n`;
			markdown += `---\n\n## Comments\n\n`;

			comments.forEach((comment: any) => {
				if (comment.kind === 't1') {
					markdown += `**${comment.data.author}** (${comment.data.score}):\n\n`;
					markdown += `${comment.data.body}\n\n`;
				}
			});

			let finalContent = markdown;
			if (this.settings.fileFormat === 'html') {
				// A simple conversion, for a real implementation, a library would be better
				finalContent = markdown.replace(/\n/g, '<br>');
			}

			let filePath = this.settings.saveLocation;
			if (this.settings.useTimestampedDirectories) {
				const now = new Date();
				const year = now.getFullYear();
				const month = (now.getMonth() + 1).toString().padStart(2, '0');
				const day = now.getDate().toString().padStart(2, '0');
				filePath += `${year}-${month}-${day}/`;
			}

			if(filePath !== '' && !await this.app.vault.adapter.exists(filePath)) {
				await this.app.vault.createFolder(filePath);
			}

			const fileName = `${post.title.replace(/[^\w\s]/gi, '')}.${this.settings.fileFormat}`;
			const fullPath = `${filePath}${fileName}`;

			const fileExists = await this.app.vault.adapter.exists(fullPath);
			if (fileExists && !this.settings.overwriteExistingFile) {
				new Notice('File already exists. To overwrite, enable "Overwrite Existing File" in settings.');
				return;
			}

			await this.app.vault.adapter.write(fullPath, finalContent);

			new Notice(`Successfully saved post to ${fullPath}`);
		} catch (error) {
			new Notice("Error fetching or saving post. See console for details.");
			console.error(error);
		}
	}
}

class RedditMarkdownSettingTab extends PluginSettingTab {
	plugin: RedditMarkdownPlugin;

	constructor(app: App, plugin: RedditMarkdownPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const {containerEl} = this;

		containerEl.empty();

		containerEl.createEl('h2', {text: 'Reddit Markdown Settings'});

		new Setting(containerEl)
			.setName('Reddit API URL')
			.setDesc('The base URL for the Reddit API.')
			.addText(text => text
				.setPlaceholder('https://www.reddit.com')
				.setValue(this.plugin.settings.redditApiUrl)
				.onChange(async (value) => {
					this.plugin.settings.redditApiUrl = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Save Location')
			.setDesc('The default location to save Reddit posts. If empty, it will save to the vault root.')
			.addText(text => text
				.setPlaceholder('reddit-posts/')
				.setValue(this.plugin.settings.saveLocation)
				.onChange(async (value) => {
					this.plugin.settings.saveLocation = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Use Timestamped Directories')
			.setDesc('Create a new directory for each day’s posts (e.g., YYYY-MM-DD).')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.useTimestampedDirectories)
				.onChange(async (value) => {
					this.plugin.settings.useTimestampedDirectories = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('File Format')
			.setDesc('Choose the file format for saved posts.')
			.addDropdown(dropdown => dropdown
				.addOption('markdown', 'Markdown')
				.addOption('html', 'HTML')
				.setValue(this.plugin.settings.fileFormat)
				.onChange(async (value: 'markdown' | 'html') => {
					this.plugin.settings.fileFormat = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Overwrite Existing File')
			.setDesc('If a file with the same name already exists, overwrite it.')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.overwriteExistingFile)
				.onChange(async (value) => {
					this.plugin.settings.overwriteExistingFile = value;
					await this.plugin.saveSettings();
				}));

		containerEl.createEl('h3', {text: 'Authentication'});

		new Setting(containerEl)
			.setName('Login on Startup')
			.setDesc('Automatically log in to Reddit when Obsidian starts.')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.loginOnStartup)
				.onChange(async (value) => {
					this.plugin.settings.loginOnStartup = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Client ID')
			.setDesc('The client ID for your Reddit application.')
			.addText(text => text
				.setPlaceholder('Your Reddit client ID')
				.setValue(this.plugin.settings.clientId)
				.onChange(async (value) => {
					this.plugin.settings.clientId = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Client Secret')
			.setDesc('The client secret for your Reddit application.')
			.addText(text => text
				.setPlaceholder('Your Reddit client secret')
				.setValue(this.plugin.settings.clientSecret)
				.onChange(async (value) => {
					this.plugin.settings.clientSecret = value;
					await this.plugin.saveSettings();
				}));

		containerEl.createEl('h3', {text: 'Updates'});

		new Setting(containerEl)
			.setName('Check for Updates on Startup')
			.setDesc('Automatically check for new versions of the plugin when Obsidian starts.')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.updateCheckOnStartup)
				.onChange(async (value) => {
					this.plugin.settings.updateCheckOnStartup = value;
					await this.plugin.saveSettings();
				}));
	}
}

class RedditUrlModal extends Modal {
	url: string;
	onSubmit: (url: string) => void;

	constructor(app: App, onSubmit: (url: string) => void) {
		super(app);
		this.onSubmit = onSubmit;
	}

	onOpen() {
		const {contentEl} = this;

		contentEl.createEl("h2", { text: "Enter Reddit Post URL" });

		const textInput = new Setting(contentEl)
			.addText((text) => {
				text.setPlaceholder("https://www.reddit.com/...");
				text.onChange((value) => {
					this.url = value;
				});
			});

		new Setting(contentEl)
			.addButton((btn) =>
				btn
					.setButtonText("Fetch")
					.setCta()
					.onClick(() => {
						this.close();
						this.onSubmit(this.url);
					}));
	}

	onClose() {
		let {contentEl} = this;
		contentEl.empty();
	}
}

