require 'rubygems'
require 'json'
require 'open-uri' 
require 'uri'

puts "This script saves the content (body and replies) of a Reddit post to a Markdown file for easy reading, sharing, and archiving."

# Supported colors to differentiate between replies of different depths.
colors = [
    "🟩",
    "🟨",
    "🟧",
    "🟦",
    "🟪",
    "🟥",
    "🟫",
    "🟤",
    "⬛️",
    "⬜️"
]

puts "\n"

# Example of a "clean" Reddit link
# This script also supports links that have other query parameters appended (that happens when you use the "Share" button to get the link)
# https://www.reddit.com/r/pcmasterrace/comments/101kjyq/my_dad_has_been_playing_civilization_almost_daily/

puts "Enter the link to the Reddit post that you want to save:"
url = gets.chomp

# URLs that are shared from Reddit may have query parameters appended.
# Drop them to get a clean URL.
if url.include? "?utm_source"
    url = url.split("?utm_source").first
end

if url == nil || url == ""
    puts "Error: URL is empty. Try again."
    exit
end
 
puts "\n"
puts "Downloading post data..."

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

# Use the last part of the URL (after the last slash) for the file name.
file_name = url.split("/").last

# The entire JSON payload
json = download_post_json(url)

if json == nil || json == ""
    puts "Error: JSON payload is empty. Try again."
    exit
end

# The post body and relevant metadata
post_info = json[0]['data']['children']

# The replies
response = json[1]['data']['children']

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

content = "**#{post_info[0]['data']['subreddit_name_prefixed']}** | Posted by u/#{post_info[0]['data']['author']}\n\n"
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
    content += "* #{colors[0]} **#{reply['data']['author']}** ⬆️ #{reply['data']['ups']} ⬇️ #{reply['data']['downs']}  \n"

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
        content += "* #{colors[child_reply['depth']]} **#{child_reply['child_reply']['data']['author']}** ⬆️ #{child_reply['child_reply']['data']['ups']} ⬇️ #{child_reply['child_reply']['data']['downs']}  \n"

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
end

content += "\n"

puts "\n"
puts "Enter a path to save the file to. Leave blank for current directory (where you called the script from):"
directory = gets.chomp

if directory == ""
    directory = Dir.pwd
end

if !Dir.exist?(directory)
    puts "Invalid directory. Exiting."
    exit
end

# If the file already exists, still save it but append a number to the file name.
# There is value in having multiple copies of the same post saved, especially if the post/replies have been updated.
copy_num = 0

if (File.exist?("#{directory}/#{file_name}.md"))
    copy_num += 1

    while File.exist?("#{directory}/#{file_name}_#{copy_num}.md")
        copy_num += 1
    end    
end

if copy_num > 0
    puts "File with name #{file_name}.md already exists. Renaming to #{file_name}_#{copy_num}.md...\n\n"
    file_name = "#{file_name}_#{copy_num}"
end

puts "Saving to #{directory}/#{file_name}.md...\n\n"

File.open("#{file_name}.md", "w") { |file| file.write(content) }

puts "Reddit post saved! Check #{directory}/#{file_name}.md."
