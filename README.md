# reddit-markdown

## Introduction
This script saves Reddit posts into local Markdown files for easy reading, sharing, and archiving. Both post body and replies are supported. You can then use any Markdown reader or knowledge management software to manage the saved posts.

<div>
	<img src="https://chauduyphanvu.s3.us-east-2.amazonaws.com/screenshots/Reddit_Markdown_Raw.png" width="49%" />
	<img src="https://chauduyphanvu.s3.us-east-2.amazonaws.com/screenshots/Reddit_Markdown_Rendered.png" width="49%" />
</div>

## Coming Soon

The command line can be intimidating for some users, so I'm working on a graphical user interface (GUI) to make the script more accessible.
It's going to be a self-hosted web app that you can run locally on your machine. 

This particular feature is a work in progress. Here's a sneak peek of what's coming:

<img src="https://chauduyphanvu.s3.us-east-2.amazonaws.com/screenshots/Reddit_Markdown_UI.png" width="100%" />

Note: UI details are subject to change. Stay tuned for more updates!

## Usage
1. **Install Ruby/Python on your device**
    * Depending on the version you want to use, you need to install Ruby or Python on your device.
      * If you are using the Ruby version, you can download it from [here](https://www.ruby-lang.org/en/downloads/).
      * If you are using the Python version, you can download it from [here](https://www.python.org/downloads/).
2. **Download the [latest release](https://github.com/chauduyphanvu/reddit-markdown/releases) of this script**
3. **Open a terminal**
4. **Run the script with the following command:**
    * `ruby reddit-markdown.rb` or `python reddit-markdown.py`
    * If you call the script from a different folder, you need to specify the path to the script
        * `ruby /path/to/reddit-markdown.rb` or `python /path/to/reddit-markdown.py`
	* Tip: Starting with the 1.7.0 release, command-line arguments are supported. See [Command-line Arguments](#command-line-arguments) for details. If you use that option, you can skip the next step.
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

## Command-line Arguments
Starting with the 1.7.0 release, command-line arguments are supported to facilitate automation and integration with other programs (see [Automation](#automation) for details)

This is in addition to the existing interactive mode. You can pass input to the script via either method (to use the interactive mode, simply do not pass any command-line arguments). However, in the future, the interactive mode is scheduled to be removed, so it is recommended to adopt command-line arguments as soon as possible.

The following arguments are available:

| Argument | Description | Example |
| --- | --- | --- |
| `--urls` | One or more comma-separated Reddit post URLs | `--urls https://www.reddit.com/r/corgi/comments/abc123,https://www.reddit.com/r/askreddit/comments/def456` |
| `--src-files` | One or more directory paths pointing to files containing comma-separated URLs | `--src-files path/to/urls.csv,path/to/urls.txt` |
| `--subs` | One or more comma-separated subreddit names | `--subs r/corgi,r/askreddit` |
| `--multis` | One or more comma-separated multireddit names | `--multis m/travel,m/programming` |
| `-h` or `--help` | Display help information | `--help` |

**Tip**: _You can use multiple options at once! For example, you can pass in a list of URLs, a list of subreddits, and a list of multireddits, and the script will save all of them._

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
| "reply_depth_max" | The maximum depth of replies to save. If set to -1, all replies will be saved. If set to 0, only top-level replies will be saved, so on and so forth. | Integer |
| "reply_depth_color_indicators" | Whether to render color indicators for reply depths | true/false |
| "line_break_between_parent_replies" | Whether to render a line break between parent replies | true/false |
| "show_auto_mod_comment" | Whether to render AutoModerator's comment | true/false |
| "overwrite_existing_file" | Whether to overwrite existing file if the file name already exists. If set to `false`, a number (starting with 1) will be appended to the file name. | true/false |
| "save_posts_by_subreddits" | Whether to separate saved files into subfolders named after their subreddits. If set to `true`, the subreddit name will be the name of the subfolder. If set to `false`, files will be saved together under `default_save_location` or a user-provided path. | true/false |
| "default_save_location" | The default path to save the Markdown file(s). If `save_posts_by_subreddits` is set to `true`, the subreddit name will be appended to the default path. | Path string set as an environment variable <sup>1</sup> |
| "use_timestamped_directories" | Whether to save files in timestamped directories. If set to `true`, the timestamp will be appended to the path. See [Timestamped Directories](#timestamped-subdirectories) for details. | true/false |
| "show_timestamp" | Whether to render the timestamp of the replies. If `true`, the timestamp will be converted to the local timezone. | true/false |
| "filtered_message" | The message to show when a reply is filtered out. | String |
| "filters" -> "keywords" | The list of keywords against which the replies will be filtered. If a reply contains any of the keywords, it will be filtered out. Keywords are case-sensitive. Leave Array empty to disable filtering. | Array of strings |
| "filters" -> "min_upvotes" | The minimum number of upvotes a reply must have to be saved. For example, if set to 1, only replies with 1 or more upvotes will be saved. | Integer |
| "filters" -> "authors" | The list of authors against which the replies will be filtered. If a reply is written by any of the authors, it will be filtered out. This is an exact match. Leave Array empty to disable filtering. | Array of strings |
| "filter" -> "regex" | Regular expressions against which the replies will be filtered. If a reply matches the regular expression, it will be filtered out. Leave Array empty to disable filtering. | Array of strings |
| "multi_reddits" | The list of multireddits (each is a collection of multiple subreddits) | Parent is Object. Children are Arrays of subreddit names as Strings |

<sub>1. _The path string must be set as an environment variable. The key name in `settings.json` and for your environment variable must be `DEFAULT_REDDIT_SAVE_LOCATION`. See [Use environment variables in Terminal on Mac](https://support.apple.com/guide/terminal/use-environment-variables-apd382cc5fa-4f58-4449-b20a-41c53c006f8f/mac), [Create and Modify Environment Variables on Windows](https://docs.oracle.com/en/database/oracle/machine-learning/oml4r/1.5.1/oread/creating-and-modifying-environment-variables-on-windows.html#GUID-DD6F9982-60D5-48F6-8270-A27EC53807D0), or [How to Set Environment Variables in Linux](https://www.serverlab.ca/tutorials/linux/administration-linux/how-to-set-environment-variables-in-linux/) for more details._</sub>

## Automation
This section describes a potential workflow to automate the process of saving Reddit posts. It is not meant to be a comprehensive guide, but rather a starting point for you to build upon.

We are going to use GitHub Actions to automate the process. If you are not familiar with GitHub Actions, please read [GitHub's guide on getting started with GitHub Actions](https://docs.github.com/en/actions/learn-github-actions/understanding-github-actions) first.

Here is a sample GitHub Actions workflow which triggers the `reddit_markdown.rb` script every two hours:

```yaml
name: Fetch Reddit posts

on:
  workflow_dispatch:
  schedule:
    - cron: '0 */2 * * *'

jobs:
  run_ruby_script:
    runs-on: self-hosted

    steps:
    - name: Check out repository
      uses: actions/checkout@v3
	
	- name: Set up Ruby
	  uses: ruby/setup-ruby@v1
	  with:
		ruby-version: 2.7

    - name: Run script
      run: |
        ruby reddit_markdown.rb --multis m/fav,m/stocks,m/programming,m/travel
```

You can customize this workflow according to your needs. For example, you can modify the `cron` schedule to adjust the frequency of the script execution, or change the command-line arguments to others (see [Command-line arguments](#command-line-arguments) for more details).

The above workflow uses a self-hosted runner for convenience. To set up a self-hosted runner, please read [GitHub's guide on setting up a self-hosted runner](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners) first. If you prefer to use a GitHub-hosted runner, you might need to set up additional steps to appropriately save and retrieve the downloaded Markdown files from that runner (e.g. by uploading them to a cloud storage service such as S3 and downloading them back to your local machine if needed).

## Timestamped subdirectories

Starting in v1.9.0, the feature to organize posts into timestamped directories is now available. By default, this feature is disabled to maintain backward compatibility.
To enable the feature, open the `settings.json` file and set the `use_timestamped_directories` option to `true`. The change will take effect the next time you run the script.

Organizing posts into timestamped directories allows you to easily locate posts based on their date. For instance, saved posts with a timestamp of `2020-01-01 12:00:00` will be moved to a directory named `2020-01-01`. The new path for one of those posts will be: `<base_dir>/subreddit/2020-01-01/<post>.md`

If you have already downloaded posts prior to enabling the timestamped directories feature, you can use the `timestamped_subs.rb` script to retrospectively organize them. This will enhance your browsing experience and reduce clutter in your file system.

It's important to note that using this script is entirely optional. If you prefer to not place your posts into timestamped directories, you don't need to use it. The script is provided as a convenient tool for users who want a more organized directory structure for their saved Reddit posts.

### How it works

The script works by:

1. Scanning a base directory for `.md` files that represent saved Reddit posts.
2. For each file, it extracts the timestamp from the post's content.
3. It then uses this timestamp to create a new directory (if it doesn't already exist).
4. The script then moves the file to this new directory.

The script is smart enough to ignore files that are already in a timestamped directory.

### How to use

You will need to set the `base_dir` variable in the script to the directory where your saved Reddit posts are located. This base directory path is relative to the directory where you run this script.

Once you've done that, you can simply run the script by using the `ruby` command followed by the script name in your terminal:

```bash
ruby reddit_post_organiser.rb
```

The script will then print out log messages indicating which files it is processing, whether it's created any new directories, and whether it's moved any files.

### Caution
Make sure to back up your files before running this script to prevent any unintended data loss.

## Advantages
* **Open source, and free**
* **Automation-friendly**
* **No authentication/sign-in of any kind needed**
	* Publicly available data. Safe and no security concerns
* **Look and feel similar to browsing Reddit on desktop web**
	* Bonus: Plenty of customizations available
* **Supports both text and multimedia posts**
* **Runs anywhere Ruby/Python runs**
	* Ruby/Python is cross-platform
	* Core logic is platform-agnostic so it can be translated into any other programming languages to run anywhere
* **Markdown and HTML for universality**

## Limitations
* **Only replies that are visible by default on the web are saved**
	* Reddit hides a subset of replies based on upvotes that you can manually click to show. Those won't be saved by this script.
* **Only supported on desktop**
	* But you could remote session from a phone to run the script
* **Need Ruby/Python installed first**
* **Personal side project with limited bug fixes and features past the initial release**
	* Pull requests are welcome
