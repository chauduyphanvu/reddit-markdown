# reddit-markdown

## Introduction
This Ruby script saves Reddit posts into local Markdown files for easy reading, sharing, and archiving. Both post body and replies are supported.

<div>
	<img src="https://chauduyphanvu.s3.us-east-2.amazonaws.com/screenshots/Reddit_Markdown_Raw.png" width="49%" />
	<img src="https://chauduyphanvu.s3.us-east-2.amazonaws.com/screenshots/Reddit_Markdown_Rendered.png" width="49%" />
</div>

## Usage
1. **Install Ruby on your device**
    * https://www.ruby-lang.org/en/documentation/installation/
2. **Download the [latest release](https://github.com/chauduyphanvu/reddit-markdown/releases) of this script**
3. **Open a terminal**
4. **Run the script with the following command:**
    * `ruby reddit-markdown.rb`
    * If you call the script from a different folder, you need to specify the path to the script
        * `ruby /path/to/reddit-markdown.rb`
    * Tip: You can rename the script to anything and place it anywhere you want
5. **Enter the link(s) to the Reddit post(s) you want to save**
	* If you have multiple links, separate them by commas.
	* If you need a demo, enter `demo`.
	* If you want a surprise, enter `surprise`.
	* If you want to save currently trending posts in a subreddit, enter `r/[SUBREDDIT_NAME]`, e.g. `r/pcmasterrace`.
		* Note: This feature is only available in v1.5.0 and above.
	* If you have a multireddit (i.e. collection of multiple subreddits) defined in `settings.json`, enter its name, e.g. `m/stocks`.
		* Note: This feature is only available in v1.6.0 and above.
6. **Enter the path where you want to save the Markdown file(s)**.
	* Leave blank to save in the same folder (where you called the script from)
	* Starting from v1.4.0, posts can also be saved as HTML files. To do so, get the updated `settings.json` file from that release, and use the `file_format` option. Accepted values are `html` and `md`.
	* Tip: Starting with the 1.1.0 release, you can set a default path in the `settings.json` file. See [Custom Settings](#custom-settings) for details.

## Custom Settings
Starting with the 1.1.0 release, a number of settings can be customized. They can be found in the `settings.json` file bundled with the script. 

If you are using an older release, make sure to get the latest version of the script (plus the `settings.json` file) to tweak these settings. On the other hand, if you are on the latest release but somehow don't have the `settings.json` file, you can get it directly from this repository. 

**Note**: _Settings exposed in `settings.json` are locked to a specific version of the script. If you are using different editions of the two files, you may get unexpected results. It is recommended to always use the latest version of both files._

| Setting Flag | Description | Possible values |
| --- | --- | --- |
| "version" | The version of the script that the settings are compatible with. Do NOT change. | Semantically versioned string |
| "file_format" | The file format for saved Reddit posts | `md` or `html` |
| "update_check_on_startup" | Whether to check for updates on startup | true/false |
| "show_upvotes" | Whether to render the number of upvotes | true/false |
| "reply_depth_color_indicators" | Whether to render color indicators for reply depths | true/false |
| "line_break_between_parent_replies" | Whether to render a line break between parent replies | true/false |
| "show_auto_mod_comment" | Whether to render AutoModerator's comment | true/false |
| "overwrite_existing_file" | Whether to overwrite existing file if the file name already exists. If set to `false`, a number (starting with 1) will be appended to the file name. | true/false |
| "save_posts_by_subreddits" | Whether to separate saved files into subfolders named after their subreddits. If set to `true`, the subreddit name will be the name of the subfolder. If set to `false`, files will be saved together under `default_save_location` or a user-provided path. | true/false |
| "default_save_location" | The default path to save the Markdown file(s). If `save_posts_by_subreddits` is set to `true`, the subreddit name will be appended to the default path. | Path string set as an environment variable <sup>1</sup> |
| "show_timestamp" | Whether to render the timestamp of the replies. If `true`, the timestamp will be converted to the local timezone. | true/false |
| "filtered_message" | The message to show when a reply is filtered out. | String |
| "filters" -> "keywords" | The list of keywords against which the replies will be filtered. If a reply contains any of the keywords, it will be filtered out. Keywords are case-sensitive. Leave Array empty to disable filtering. | Array of strings |
| "filters" -> "min_upvotes" | The minimum number of upvotes a reply must have to be saved. For example, if set to 1, only replies with 1 or more upvotes will be saved. | Integer |
| "filters" -> "authors" | The list of authors against which the replies will be filtered. If a reply is written by any of the authors, it will be filtered out. This is an exact match. Leave Array empty to disable filtering. | Array of strings |
| "filter" -> "regex" | Regular expressions against which the replies will be filtered. If a reply matches the regular expression, it will be filtered out. Leave Array empty to disable filtering. | Array of strings |
| "multi_reddits" | The list of multireddits (each is a collection of multiple subreddits) | Parent is Object. Children are Arrays of subreddit names as Strings |

<sub>1. _The path string must be set as an environment variable. The key name in `settings.json` and for your environment variable must be `DEFAULT_REDDIT_SAVE_LOCATION`. See [Use environment variables in Terminal on Mac](https://support.apple.com/guide/terminal/use-environment-variables-apd382cc5fa-4f58-4449-b20a-41c53c006f8f/mac), [Create and Modify Environment Variables on Windows](https://docs.oracle.com/en/database/oracle/machine-learning/oml4r/1.5.1/oread/creating-and-modifying-environment-variables-on-windows.html#GUID-DD6F9982-60D5-48F6-8270-A27EC53807D0), or [How to Set Environment Variables in Linux](https://www.serverlab.ca/tutorials/linux/administration-linux/how-to-set-environment-variables-in-linux/) for more details._</sub>

## Advantages
* **Open source, and free**
* **No authentication/sign-in of any kind needed**
	* Publicly available data. Safe and no security concerns
* **Look and feel similar to browsing Reddit on desktop web**
	* Bonus: Plenty of customizations available
* **Supports both text and multimedia posts**
* **Runs anywhere Ruby runs**
	* Ruby is cross-platform
	* Core logic is platform-agnostic so it can be translated into any other programming languages to run anywhere
* **Markdown and HTML for universality**

## Limitations
* **Only replies that are visible by default on the web are saved**
	* Reddit hides a subset of replies based on upvotes that you can manually click to show. Those won't be saved by this script.
* **Only supported on desktop**
	* But you could remote session from a phone to run the script
* **Need Ruby installed first**
* **Personal side project with limited bug fixes and features past the initial release**
	* Pull requests are welcome
