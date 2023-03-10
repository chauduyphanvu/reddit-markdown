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
