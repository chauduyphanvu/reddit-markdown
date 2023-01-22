require 'rubygems'
require 'json'
require 'open-uri'
require 'uri'

puts "ℹ️This script saves the content (body and replies) of a Reddit post to a Markdown file for easy reading, sharing, and archiving."

unless File.exist?("settings.json")
    puts "❌Error: settings.json not found. Please get a copy of it from https://github.com/chauduyphanvu/reddit-markdown/releases. Exiting..."
    exit
end

begin
    settings = JSON.parse(File.read("settings.json"))
rescue JSON::ParserError
    puts "❌Error: Failed to parse script settings. Ensure that settings.json is valid JSON. Exiting..."
    exit
end

# It is possible for settings.json to be a valid but empty JSON object
if settings == nil || settings.empty?
    puts "❌Error: settings.json is empty. Try to get a fresh copy of it from https://github.com/chauduyphanvu/reddit-markdown/releases. Exiting..."
    exit
end

version = settings['version']
update_check_on_startup = settings['update_check_on_startup']
show_auto_mod_comment = settings['show_auto_mod_comment']
line_break_enabled = settings['line_break_between_parent_replies']
show_upvotes_enabled = settings['show_upvotes']
reply_depth_color_indicators_enabled = settings['reply_depth_color_indicators']
overwrite_existing_file_enabled = settings['overwrite_existing_file']
save_posts_by_subreddits = settings['save_posts_by_subreddits']
show_timestamp = settings['show_timestamp']

# Only apply to replies and not actual post body.
# When applied, reply body will be replaced by user-defined filtered_message.
filtered_message = settings["filtered_message"]
filtered_keywords = settings['filters']['keywords']
filtered_min_upvotes = settings['filters']['min_upvotes']
filtered_authors = settings['filters']['authors']
filtered_regexes = settings['filters']['regexes']

directory = settings["default_save_location"]

# Note: This is an approximate count only and should not be used for anything critical.
# It does not include replies that Reddit hides by default on the web experience.
# The more replies a post has, the more replies get hidden by default, and the more inaccurate this count will be.
replies_count = {}

if update_check_on_startup == true
    begin
        commits = JSON.parse(URI.open("https://api.github.com/repos/chauduyphanvu/reddit-markdown/releases").read)

        if commits.length == 0
            puts "Warning: Unable to fetch latest release info from GitHub. Please check for updates manually. The repo might have been renamed/deleted."
        end

        latest_version = commits.first["tag_name"]

        if latest_version.match?(/\d+\.\d+\.\d+/)
            if Gem::Version.new(latest_version) > Gem::Version.new(version)
                puts "\nSuggestion: A new version (#{latest_version}) is available. Your current version is #{version}. You can download the latest version from https://github.com/chauduyphanvu/reddit-markdown."
            end
        else
            puts "\nWarning: Found invalid version number in latest GitHub commit. Please check for updates manually at https://github.com/chauduyphanvu/reddit-markdown."
        end
    rescue
        puts "❌Error: Could not check for updates. Feel free to do that manually at https://github.com/chauduyphanvu/reddit-markdown."
    end
end

# Supported colors to differentiate between replies of different depths.
colors = %w[🟩 🟨 🟧 🟦 🟪 🟥 🟫 ⬛️ ⬜️]

puts "\n"

# Example of a "clean" Reddit link
# This script also supports links that have other query parameters appended (that happens when you use the "Share" button to get the link)
# https://www.reddit.com/r/pcmasterrace/comments/101kjyq/my_dad_has_been_playing_civilization_almost_daily/
puts "✏️Enter the link to the Reddit post that you want to save. Separate multiple links with commas."
puts "✏️Want a demo? Enter \"demo\"! Want a surprise? Enter \"surprise\"!"
puts "✏️That's not enough? Enter \"snapshot\" to save what's on r/popular right now!"
urls = gets.chomp

while urls == nil || urls == ""
    puts "❌Error: No links provided. Try again."
    urls = gets.chomp

    puts "\n"
end

puts "\n"

# To avoid having to enter the save location every time, you can set the DEFAULT_REDDIT_SAVE_LOCATION environment variable.
# For it to take effect, the env var must be set once BEFORE running the script, and
# the default_save_location value in settings.json must be set to "DEFAULT_REDDIT_SAVE_LOCATION".
if directory == "DEFAULT_REDDIT_SAVE_LOCATION"
    directory = ENV["DEFAULT_REDDIT_SAVE_LOCATION"]

    if directory == nil || directory == ""
        puts "❌Error: DEFAULT_REDDIT_SAVE_LOCATION environment variable not set. You must set it to a valid path before running the script.
        If you'd rather be prompted for the save location every time, set the default_save_location value in settings.json to \"\"."
        puts "Exiting..."
        exit
    end
else
    puts "=> Enter a full path to save the post(s) to. Hit Enter/Return for current directory, which is #{Dir.pwd}."
    directory = gets.chomp
    directory = directory.strip

    if directory == ""
        directory = Dir.pwd
    end

    until File.directory?(directory)
        puts "❌Error: Invalid path. Try again."
        directory = gets.chomp

        puts "\n"
    end
end

# By appending ".json" to the end of a Reddit post URL, we can get the JSON payload for the post.
# This way we don't have to actually tap into the Reddit API. No authentication is required.
#
# Note that this payload does not necessarily include all the replies. See get_replies() for more info below.
# A non-empty user agent is required so that we aren't rate limited (a sample one is provided below).
def download_post_json(url)
    URI.open(
      url + ".json",
      "User-Agent" => "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
      :read_timeout => 5
    ) {
      |f| json = JSON.parse(f.read)
        json
    }
end

# Get all the child replies to a parent (top-level) reply.
def get_replies(reply)
    child_replies = {}

    if reply['data']['replies'] != ""
        reply['data']['replies']['data']['children'].each do |child_reply|
            child_reply_id = child_reply['data']['id']
            child_reply_depth = child_reply['data']['depth']
            child_reply_body = child_reply['data']['body']

            # On the web, Reddit hides a subset of replies that you'd have to manually click to see.
            # Those replies typically have very low upvotes and are usually just spam.
            # This script preserves that experience and skips replies that fall into that category.
            if child_reply_body == nil || child_reply_body == ""
                next
            end

            child_replies[child_reply_id] = {
              'depth' => child_reply_depth,
              'child_reply' => child_reply
            }

            child_replies.merge!(get_replies(child_reply))
        end
    end

    child_replies
end

# Resolve the file name based on a number of rules.
def resolve_full_path(url, directory, overwrite_existing_file_enabled, save_posts_by_subreddits, subreddit)
    file_name = url.split("/").last
    subreddit = subreddit.gsub("r/", "")
    full_path = directory

    if save_posts_by_subreddits == true
        full_path = "#{directory}/#{subreddit}"

        unless File.directory?(full_path)
            FileUtils.mkdir_p(full_path)
        end
    end

    # If we have to use a timestamp, return early since there's no need to worry about duplicate file names.
    if file_name == nil || file_name == ""
        puts "⚠️Could not get file name from URL. Using current timestamp as file name..."
        return "#{full_path}/reddit_no_name_#{Time.now.to_i}"
    end

    full_path = "#{full_path}/#{file_name}"
    duplicates = 0

    if File.exist?("#{full_path}.md")
        if overwrite_existing_file_enabled == true
            puts "⚠️File with name #{file_name}.md already exists. Overwriting is enabled. Overwriting..."
            return "#{full_path}.md"
        end

        duplicates += 1

        while File.exist?("#{full_path}_#{duplicates}.md")
            duplicates += 1
        end
    end

    if duplicates > 0
        puts "ℹ️File with name #{file_name}.md already exists. Overwriting is disabled. Renaming to #{file_name}_#{duplicates}.md...\n"
        full_path = "#{full_path}_#{duplicates}"
    end

    "#{full_path}.md"
end

def apply_filter(author, text, upvotes, filtered_keywords, filtered_authors, min_upvotes, filtered_regex, filtered_message)
    filtered_keywords.each do |keyword|
        if text.include? keyword
            return filtered_message
        end
    end

    filtered_authors.each do |child_reply_author|
        if author == child_reply_author
            return filtered_message
        end
    end

    filtered_regex.each do |regex|
        if text.match(regex)
            return filtered_message
        end
    end

    if upvotes < min_upvotes
        return filtered_message
    end

    text
end

if urls == "demo"
    puts "🔃Demo mode enabled. Using demo link...\n\n"
    urls = "https://www.reddit.com/r/pcmasterrace/comments/101kjyq/my_dad_has_been_playing_civilization_almost_daily/"
end

if urls == "surprise"
    puts "🔃Surprise mode enabled. Saving a random post from r/popular...\n\n"

    begin
        json = download_post_json("https://www.reddit.com/r/popular")
    rescue OpenURI::HTTPError => e
        puts "❌Error downloading r/popular JSON payload: #{e.message}. Exiting..."
        exit
    end

    urls = "https://www.reddit.com" + json['data']['children'].sample['data']['permalink']
end

if urls == "snapshot"
    puts "🔃Snapshot mode enabled. Saving all current posts from r/popular...\n\n"

    begin
        json = download_post_json("https://www.reddit.com/r/popular")
    rescue OpenURI::HTTPError => e
        puts "❌Error downloading r/popular JSON payload: #{e.message}. Exiting..."
        exit
    end

    urls = ""
    json['data']['children'].each do |post|
        urls += "https://www.reddit.com" + post['data']['permalink'] + ","
    end
end

urls = urls.split(/, |,/)
urls.each_with_index do |url, index|
    url = url.strip

    # This is a trivial check to make sure the URL is somewhat valid. It is not meant to be foolproof.
    unless url.match(/https:\/\/www.reddit.com\/r\/\w+\/comments\/\w+\/\w+\/?/)
        puts "❌Error: Invalid post URL: \"#{url}\". Skipping..."
        next
    end

    puts "🔃Processing post #{index + 1} of #{urls.length}..."
    puts "#{url}"

    # URLs that are shared from Reddit may have query parameters appended.
    # Drop them to get a clean URL.
    if url.include? "?utm_source"
        url = url.split("?utm_source").first
    end

    # In case we've dropped too much. This shouldn't happen.
    if url == nil || url == ""
        puts "❌Error: Post URL is empty. Skipping..."
        next
    end

    puts "\n"
    puts "🔃Downloading post data..."

    # The entire JSON payload
    begin
        json = download_post_json(url)
    rescue OpenURI::HTTPError => e
        puts "❌Error downloading post JSON payload: #{e.message}. Skipping..."
        next
    end

    if json == nil || json == ""
        puts "❌Error: JSON payload for #{url} is empty. Skipping..."
        next
    end

    # The post body and relevant metadata
    post_info = json[0]['data']['children']

    # The replies
    response = json[1]['data']['children']

    replies_count[url] = response.length + response.map { |reply|
        # TODO: Build a hash of parent reply to child replies ONCE right here for subsequent use.
        if reply['data']['replies'] != "" && reply['data']['replies'] != nil
            get_replies(reply).length
        else
            0
        end
    }.sum

    op = post_info[0]['data']['author']
    subreddit = post_info[0]['data']['subreddit_name_prefixed']
    post_timestamp_utc = post_info[0]['data']['created_utc']
    post_timestamp = post_timestamp_utc ? Time.at(post_timestamp_utc).strftime("%Y-%m-%d %H:%M:%S") : ""

    post_upvotes = post_info[0]['data']['ups']
    post_upvotes_field = if post_upvotes
                             post_upvotes >= 1000 ? "#{post_upvotes / 1000}k" : post_upvotes
                         else
                             ""
                         end

    post_is_locked = post_info[0]['data']['locked']
    lock_message = post_is_locked ? "---\n\n>🔒 **This thread has been locked by the moderators of #{subreddit}**.\n  New comments cannot be posted" : ""

    content = "**#{subreddit}** | Posted by u/#{op} #{show_upvotes_enabled ? "⬆️ #{post_upvotes_field}" : ""} #{show_timestamp ? "_(#{post_timestamp})_" : ""}\n\n"
    content += "## #{post_info[0]['data']['title']}\n\n"
    content += "Original post: [#{post_info[0]['data']['url']}](#{post_info[0]['data']['url']})\n\n"
    content += lock_message + "\n\n" if lock_message != ""

    # The post body as text, if any
    post_text = "#{post_info[0]['data']['selftext'].gsub(/\n/, "\n> ")}"

    # The post body as a media, if any
    # This will get the first one if there's only one.
    # We currently don't support multiple medias in a single post (post body and replies will still be downloaded but medias will be ignored).
    post_media_url = post_info[0]['data']['url_overridden_by_dest']

    image_extensions = %w[.jpg .jpeg .png .gif]
    youtube_domains = %w[youtube.com youtu.be]

    if post_media_url != nil && post_media_url != ""
        if image_extensions.any? { |ext| post_media_url.include? ext }
            content += "![#{post_info[0]['data']['title']}](#{post_media_url})\n\n"
        else
            # Start by supporting YouTube videos only. Also, videos won't play inline like GIFs do.
            # We'll get the first frame and display it as an image for external clickthroughs.
            if youtube_domains.any? { |domain| post_media_url.include? domain }
                youtube_id = if post_media_url.include? "watch?v="
                                 post_media_url.split("watch?v=").last
                             else
                                 post_media_url.split("/").last
                             end
                content += "[![#{post_info[0]['data']['title']}](https://img.youtube.com/vi/#{youtube_id}/0.jpg)](#{post_media_url})\n\n"
            end
        end
    end

    if post_text != nil && post_text != ""
        content += "> #{post_text}\n\n"
    end

    content += "💬 ~ #{replies_count[url]} replies\n\n"
    content += "---\n\n"

    response[0...response.length].each do |reply|
        author = reply['data']['author']

        # In some cases the author field is empty in the JSON payload.
        if author == nil || author == ""
            next
        end

        if author == "AutoModerator" && show_auto_mod_comment == false
            next
        end

        author_field = author
        if author != "[deleted]"
            author_field = "[#{author}](https://www.reddit.com/user/#{author})"
        end

        if author == op
            author_field += " (OP)"
        end

        timestamp_utc = reply['data']['created_utc']
        timestamp = timestamp_utc ? Time.at(timestamp_utc).strftime("%Y-%m-%d %H:%M:%S") : ""
        upvotes = reply['data']['ups']
        upvotes_field = if upvotes
                            upvotes >= 1000 ? "#{upvotes / 1000}k" : upvotes
                        else
                            ""
                        end

        content += "* #{reply_depth_color_indicators_enabled ? colors[0] : ""} **#{author_field}** #{show_upvotes_enabled ? "⬆️ #{upvotes_field}" : ""} #{show_timestamp ? "_(#{timestamp})_" : ""}\n\n"

        # Parent (1st-level) reply, from which we'll get all the child replies.
        reply_body = reply['data']['body']

        # On the web, Reddit hides a subset of child replies that you'd have to manually click to see.
        # Those child replies typically have very low upvotes and are usually just spam.
        # This script preserves that experience and skips child replies that fall into that category.
        if reply_body == nil || reply_body == ""
            next
        end

        if reply_body == "[deleted]"
            reply_formatted = "Comment deleted by user"
        else
            # Some Reddit replies have erratic new lines. This fixes that to some extent.
            reply_formatted = reply_body.squeeze("\n")
            reply_formatted = reply_formatted.squeeze("\r")
            reply_formatted = reply_formatted.gsub(/\n/, "\n\n\t")

            # Properly render quotes
            reply_formatted = reply_formatted.gsub(/&gt;/, ">")

            # See if reply contain u/username and replace it with [username](https://www.reddit.com/user/username)
            reply_formatted = reply_formatted.gsub(/u\/(\w+)/, '[u/\1](https://www.reddit.com/user/\1)')
            reply_formatted = apply_filter(author, reply_formatted, upvotes, filtered_keywords, filtered_authors, filtered_min_upvotes, filtered_regexes, filtered_message)
        end

        content += "\t#{reply_formatted}\n\n"

        child_replies = get_replies(reply)

        child_replies.each do |_, child_reply|
            content += "\t" * child_reply['depth']
            author = child_reply['child_reply']['data']['author']

            author_field = author
            if author != "[deleted]"
                author_field = "[#{author}](https://www.reddit.com/user/#{author})"
            end

            if author == op
                author_field += " (OP)"
            end

            timestamp_utc = child_reply['child_reply']['data']['created_utc']
            timestamp = timestamp_utc ? Time.at(timestamp_utc).strftime("%Y-%m-%d %H:%M:%S") : ""
            upvotes = child_reply['child_reply']['data']['ups']
            upvotes_field = if upvotes
                                upvotes >= 1000 ? "#{upvotes / 1000}k" : upvotes
                            else
                                ""
                            end

            content += "* #{reply_depth_color_indicators_enabled ? colors[child_reply['depth']] : ""} **#{author_field}** #{show_upvotes_enabled ? "⬆️ #{upvotes_field}" : ""} #{show_timestamp ? "_(#{timestamp})_" : ""}\n\n"

            # Have a different indentation for child reply depending on its depth.
            tabs = "\t"
            child_reply['depth'].times do |_|
                tabs += "\t"
            end

            child_reply_body = child_reply['child_reply']['data']['body']

            if child_reply_body == "[deleted]"
                child_reply_formatted = "Comment deleted by user"
            else
                # Format the child reply body such that each *subsequent new line* is indented by the depth of the reply.
                # Some Reddit replies have erratic new lines. This fixes that to some extent.
                child_reply_formatted = child_reply_body.gsub(/\n/, "\n#{tabs}")

                # Properly render quotes
                child_reply_formatted = child_reply_formatted.gsub(/&gt;/, ">")

                # Band-aid fix for when some bots replies with signatures tend to be broken
                child_reply_formatted = child_reply_formatted.gsub(/&amp;#32;/, " ")
                child_reply_formatted = child_reply_formatted.gsub(/\^\[/, "[")
                child_reply_formatted = child_reply_formatted.gsub(/\^\(/, "(")

                # See if reply contain u/username and replace it with [username](https://www.reddit.com/user/username)
                child_reply_formatted = child_reply_formatted.gsub(/u\/(\w+)/, '[u/\1](https://www.reddit.com/user/\1)')
                child_reply_formatted = apply_filter(author, child_reply_formatted, upvotes, filtered_keywords, filtered_authors, filtered_min_upvotes, filtered_regexes, filtered_message)
            end

            # The formatted child reply still needs to be indented by x number of tabs for the first line.
            content += "#{tabs}#{child_reply_formatted}\n\n"
        end

        if line_break_enabled == true
            content += "---\n\n"
        end
    end

    content += "\n"
    full_path = resolve_full_path(url, directory, overwrite_existing_file_enabled, save_posts_by_subreddits, subreddit)

    puts "🔃Saving...\n"

    File.open(full_path, "w") { |file| file.write(content) }

    puts "✅Reddit post saved! Check it out at #{full_path}."
    puts "\n---\n"
end

puts "Thanks for using this script!\n"
puts "Something's not working as expected? Have a feature you'd like to see added? Let me know by opening an issue on GitHub at https://github.com/chauduyphanvu/reddit-markdown/issues."
