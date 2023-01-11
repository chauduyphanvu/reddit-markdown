require 'rubygems'
require 'json'
require 'open-uri' 
require 'uri'

puts "This script saves the content (body and replies) of a Reddit post to a Markdown file for easy reading, sharing, and archiving."

if !File.exist?("settings.json")
    puts "Error: settings.json not found. Please get a copy of it from https://github.com/chauduyphanvu/reddit-markdown/releases. Exiting..."
    exit
end

settings = JSON.parse(File.read("settings.json"))

version = settings['version']
update_check_on_startup = settings['update_check_on_startup']
show_auto_mod_comment = settings['show_auto_mod_comment']
line_break_enabled = settings['line_break_between_parent_replies']
show_upvotes_enabled = settings['show_upvotes']
reply_depth_color_indicators_enabled = settings['reply_depth_color_indicators']
overwrite_existing_file_enabled = settings['overwrite_existing_file']
save_posts_by_subreddits = settings['save_posts_by_subreddits']
directory = settings["default_save_location"]

if update_check_on_startup == true
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
end

# Supported colors to differentiate between replies of different depths.
colors = [
    "🟩",
    "🟨",
    "🟧",
    "🟦",
    "🟪",
    "🟥",
    "🟫",    
    "⬛️",
    "⬜️"
]

puts "\n"

# Example of a "clean" Reddit link
# This script also supports links that have other query parameters appended (that happens when you use the "Share" button to get the link)
# https://www.reddit.com/r/pcmasterrace/comments/101kjyq/my_dad_has_been_playing_civilization_almost_daily/
puts "=> Enter the link to the Reddit post that you want to save. Separate multiple links with commas."
urls = gets.chomp

while urls == nil || urls == ""
    puts "Error: No links provided. Try again."
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
        puts "Error: DEFAULT_REDDIT_SAVE_LOCATION environment variable not set. You must set it to a valid path before running the script. 
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
        
    while (!File.directory?(directory)) 
        puts "Error: Invalid path. Try again."
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

        if !File.directory?(full_path)
            FileUtils.mkdir_p(full_path)
        end
    end
            
    # If we have to use a timestamp, no need to worry about duplicate file names.
    if file_name == nil || file_name == ""
        puts "Error: Could not get file name from URL. Using current timestamp as file name..."
        return "#{full_path}/reddit_no_name_#{Time.now.to_i}"
    end

    full_path = "#{full_path}/#{file_name}"
    copy_num = 0

    if (File.exist?("#{full_path}.md"))
        if overwrite_existing_file_enabled == true
            puts "File with name #{file_name}.md already exists. Overwriting is enabled. Overwriting..."
            return "#{full_path}.md"
        end
    
        copy_num += 1

        while File.exist?("#{full_path}_#{copy_num}.md")
            copy_num += 1
        end    
    end

    if copy_num > 0
        puts "File with name #{file_name}.md already exists. Overwriting is disabled. Renaming to #{file_name}_#{copy_num}.md...\n"
        full_path = "#{full_path}_#{copy_num}"
    end

    "#{full_path}.md"
end

urls = urls.split(",")
urls.each_with_index do |url, index|
    puts "#{index + 1}. #{url}"

    # URLs that are shared from Reddit may have query parameters appended.
    # Drop them to get a clean URL.
    if url.include? "?utm_source"
        url = url.split("?utm_source").first
    end

    if url == nil || url == ""
        puts "Error: Invalid URL. Skipping..."
        next
    end

    puts "\n"
    puts "Downloading post data..."

    # The entire JSON payload
    json = download_post_json(url)

    if json == nil || json == ""
        puts "Error: JSON payload for #{url} is empty. Skipping..."
        next
    end

    # The post body and relevant metadata
    post_info = json[0]['data']['children']

    # The replies
    response = json[1]['data']['children']

    op = post_info[0]['data']['author']
    subreddit = post_info[0]['data']['subreddit_name_prefixed']
    content = "**#{subreddit}** | Posted by u/#{op}\n\n"
    content += "## #{post_info[0]['data']['title']}\n\n"
    content += "Original post: [#{post_info[0]['data']['url']}](#{post_info[0]['data']['url']})\n\n"

    # The post body as text, if any
    post_text = "#{post_info[0]['data']['selftext'].gsub(/\n/, "\n> ")}"

    # The post body as a media, if any
    # This will get the first one if there's only one. 
    # We currently don't support multiple medias in a single post (post body and replies will still be downloaded but medias will be ignored).
    post_media = post_info[0]['data']['url_overridden_by_dest']

    if post_media != nil && post_media != ""
        content += "![#{post_info[0]['data']['title']}](#{post_media})\n\n"
    end

    if post_text != nil && post_text != ""
        content += "> #{post_text}\n\n"
    end

    content += "---\n\n"

    response[0...response.length].each do |reply|            
        author = reply['data']['author']

        if author == "AutoModerator" && show_auto_mod_comment == false
            next
        end

        if author == op
            author += " (OP)"
        end

        content += "* #{reply_depth_color_indicators_enabled ? colors[0] : ""} **#{author}** #{show_upvotes_enabled ? "⬆️ #{reply['data']['ups']}" : ""}\n\n"

        # Parent (1st-level) reply, from which we'll get all the child replies.
        reply_body = reply['data']['body']

        # On the web, Reddit hides a subset of child replies that you'd have to manually click to see.
        # Those child replies typically have very low upvotes and are usually just spam.
        # This script preserves that experience and skips child replies that fall into that category.
        if reply_body == nil || reply_body == ""
            next
        end

        # Format the reply body such that each new line is properly indented.
        # Also if the reply body contains `&gt;`, replace it with `>` so quotes properly show up.
        reply_formatted = reply_body.gsub(/\n/, "\n\t")
        reply_formatted = reply_formatted.gsub(/&gt;/, ">")
        content += "\t#{reply_formatted}\n\n"

        child_replies = get_replies(reply)
        child_replies.each do |id, child_reply|
            content += "\t" * child_reply['depth']
            author = child_reply['child_reply']['data']['author']

            if author == op
                author += " (OP)"
            end

            content += "* #{reply_depth_color_indicators_enabled ? colors[child_reply['depth']] : ""} **#{author}** #{show_upvotes_enabled ? "⬆️ #{child_reply['child_reply']['data']['ups']}" : ""}\n\n"

            # Have a different indentation for child reply depending on its depth.
            tabs = "\t"
            child_reply['depth'].times do |i| 
                tabs += "\t"
            end

            # Format the child reply body such that each *subsequent new line* is indented by the depth of the reply.
            # Also if the child reply body contains `&gt;`, replace it with `>` so quotes properly show up.
            child_reply_formatted = child_reply['child_reply']['data']['body'].gsub(/\n/, "\n#{tabs}")
            child_reply_formatted = child_reply_formatted.gsub(/&gt;/, ">")

            # The formatted child reply still needs to be indented by x number of tabs for the first line.
            content += "#{tabs}#{child_reply_formatted}\n\n"
        end

        if line_break_enabled == true
            content += "---\n\n"
        end
    end

    content += "\n"
    full_path = resolve_full_path(url, directory, overwrite_existing_file_enabled, save_posts_by_subreddits, subreddit)

    puts "Saving to #{full_path}...\n"

    File.open(full_path, "w") { |file| file.write(content) }

    puts "Reddit post saved! Check it out at #{full_path}."
    puts "\n---\n"
end
