require 'optparse'

class CommandLineArgs
    attr_reader :urls, :src_files, :subs, :multis

    def initialize
        @urls = []
        @src_files = []
        @subs = []
        @multis = []

        parse_options
    end

    private

    def parse_options
        OptionParser.new do |opts|
            opts.banner = "Usage: ruby reddit_markdown.rb [options]"

            opts.on('--urls URLS', Array, 'One or more comma-separated Reddit post URLs') do |urls|
                @urls.concat(urls)
            end

            opts.on('--src-files FILES', Array, 'One or more directory paths pointing to files containing comma-separated URLs') do |files|
                @src_files.concat(files)
            end

            opts.on('--subs SUBREDDITS', Array, 'One or more comma-separated subreddit names (e.g. r/corgi,r/askreddit)') do |subreddits|
                @subs.concat(subreddits)
            end

            opts.on('--multis MULTIS', Array, 'One or more comma-separated multireddit names (e.g. m/travel,m/programming)') do |multireddits|
                @multis.concat(multireddits)
            end

            opts.on('-h', '--help', 'Display help information') do
                puts "This script saves the content (body and replies) of a Reddit post to a Markdown file for easy reading, sharing, and archiving. The options are:"
                puts opts
                puts "\nExample usage:"
                puts "  ruby reddit_markdown.rb --urls https://www.reddit.com/r/ruby/comments/abc123"
                puts "  ruby reddit_markdown.rb --src-files path/to/urls.csv"
                puts "  ruby reddit_markdown.rb --subs r/corgi,r/askreddit"
                puts "  ruby reddit_markdown.rb --multis m/travel,m/programming"
                puts "\nTip: You can use multiple options at once!"
                exit
            end
        end.parse!
    end
end
