## 1.11.0 (Mar 16, 2025)
### Improvements
* Refactor the Python script for better readability and maintainability. No functional changes.

## 1.10.0 (Mar 13, 2025)
### New
* Debut the Python version of the script! 🎉
    * The Python version is now available in the `python` directory.
    * It is a direct port of the Ruby version, so all features are available.
    * It is now the primary version of the script (i.e. new features will be added to the Python version first and then ported to the Ruby version if necessary).

## 1.9.0 (Jul 04, 2023)
### New
* Add support for organizing saved posts by timestamp (e.g. `2023-07-04`). See README for details.

## 1.8.0 (Jun 17, 2023)
### New
* N/A
### Improvements
* Add the Gemfile for easier dependency management
* Gracefully fail when a subreddit is not found (e.g. it's been banned or gone private)
### Bug Fixes
* N/A

## 1.7.1 (Apr 29, 2023)
### New
* N/A
### Improvements
* Consolidate the JSON download logic for reuse. Also, the previous implementation was not running well on Windows.
### Bug Fixes
* N/A

## 1.7.0 (Apr 28, 2023)
### New
* Add support for command-line arguments. See README for details.
* Add support for a maximum reply depth. See README for details.
### Improvements
* N/A
### Bug Fixes
* N/A

## 1.6.0 (Apr 20, 2023)
### New
* **Download trending posts from a multireddit**
    * Define your own multireddit in `settings.json` or use one of the default ones for a quick start.
    * Type `m/<multireddit_name>`, e.g. `m/stocks` when prompted.
### Improvements
* N/A
### Bug Fixes
* N/A

## 1.5.0 (Apr 19, 2023)
### New
* **Download trending posts from a subreddit**
    * Type `r/<subreddit_name>`, e.g. `r/AskReddit` when prompted.
    * `snapshot` mode has been superseded by this feature.
### Improvements
* **Improve error handling during download**
* **Rewrite input mode selection logic for better code separation**
* **Rewrite update checking logic for conciseness**
### Bug Fixes
* N/A

## 1.4.0 (Apr 08, 2023)
### New
* **Add support for saving posts as HTML files**
    * Get the updated `settings.json` file from this release, and use the `file_format` option. Accepted values are `html` and `md`.
### Improvements
* **Minor refactoring for ease of maintenance**
### Bug Fixes
* **Fix a Reddit encoding issue with `&amp;` in post body that cause image URLs to be broken**

## 1.3.0 (Jan 21, 2023)
### New
* **Filter replies against user-defined regex(es)**
* **Save all posts from *r/popular* at the moment**
	* Type `snapshot` when prompted.
* **Support embedded YouTube media in post body**
    * Additional support for other video platforms will be added in the future.
### Improvements
* **Support post timestamp**
	* Reply timestamps were added in v1.2.0
* **Render if a post has been locked by mods**
* **Hyperlink other author(s) mentioned in replies**
* **Render post-level upvotes in addition to reply-level upvotes**
* **Render upvotes over 1000 with the `k` notation**
* **Indicate whether a comment has been deleted by the user**
* **Handle checking for updates getting rate limited**
* **Safely handle JSON payload parsing**
* **Handle URL validation**
* **Render replies count (approx.)**
### Bug Fixes
* **Fix bot replies broken when there's a signature**
* **Fix final reply broken when rendered**

## 1.2.0 (Jan 14, 2023)
### New
* **Add a demo**
    * First time trying this script? Typing `demo` when prompted to have a quick demo.
* **Surprise me**
    * Typing `surprise` when prompted to save a random URL from r/popular.
* **Filter replies**
    * Filter replies via the following criteria:
      * Against predefined keyword(s)
      * Based on min # of upvotes
      * Based on author(s)
### Improvements
* **Split multi-URLs input by both `,` and `, `**
* **Hyperlink reply authors**
* **Render reply timestamps**
### Bug Fixes
* N/A

## 1.1.0 (Jan 10, 2023)
### New
* **Support saving multiple posts at once**. When prompted, paste all your links separated by commas
* **Support user custom settings**. See README for details.
* **Automatically check for new script releases**
### Improvements
* **Show OP indicator next to author when replies are from OP**
* **Remove downvotes rendering**. They are always 0. Downvotes reduce upvotes so showing only upvotes is sufficient.
* **Remove the depth indicator 🟤**—for consistency with all the others, which are squares
### Bug Fixes
* **Fix a bug preventing saving when a custom path is provided**

## 1.0.0 (Jan 5, 2023)
* Initial release
