require 'fileutils'
require 'date'

# Starting in v1.9.0, the feature to organize posts into timestamped directories is now available. By default, this feature is disabled to maintain backward compatibility.
# To enable the feature, open the `settings.json` file and set the `use_timestamped_directories` option to `true`. The change will take effect the next time you run the script.
#
# Organizing posts into timestamped directories allows you to easily locate posts based on their date.
# For instance, saved posts with a timestamp of `2020-01-01 12:00:00` will be moved to a directory named `2020-01-01`. The new path for one of those posts will be: `<base_dir>/subreddit/2020-01-01/<post>.md`
#
# If you have already downloaded posts prior to enabling the timestamped directories feature, you can use this script to retrospectively organize them.
# This will enhance your browsing experience and reduce clutter in your file system.
#
# It's important to note that using this script is entirely optional. If you prefer to not place your posts into timestamped directories, you don't need to use it. The script is provided as a convenient tool for users who want a more organized directory structure for their saved Reddit posts.

# Edit this to the base directory where you downloaded your Reddit posts.
# Note: This base directory path is relative to the directory where you run this script.
base_dir = '../Downloads/Reddit/'

# Maximum number of threads to use
max_threads = 5

queue = Queue.new

Dir.glob("#{base_dir}/**/*.md") do |file|
  queue.push(file)
end

workers = (1..max_threads).map do
  Thread.new do
    while (file = queue.pop(true)) rescue nil
      puts "Processing file: #{file}"

      if File.dirname(file).match?(/\d{4}-\d{2}-\d{2}/) # YYYY-MM-DD
        puts "File is already in a timestamped directory: #{file}"
        next
      end

      timestamp = nil

      begin
        File.foreach(file) do |line|
          match = line.match(/\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\)/) # (YYYY-MM-DD HH:MM:SS)
          if match
            timestamp = match
            break
          end
        end
      rescue StandardError => e
        puts "Error reading file: #{file}. Error: #{e.message}"
        next
      end
      
      if timestamp.nil?
        puts "No timestamp found in file: #{file}. Skipping."
      else
        begin
          date = Date.parse(timestamp[0][1...-1])
          date_string = date.strftime('%Y-%m-%d') # YYYY-MM-DD
        rescue StandardError => e
          puts "Error parsing date: #{file}. Error: #{e.message}"
          next
        end

        subdir = File.dirname(file).split('/')[-1]
        new_dir = "#{base_dir}/#{subdir}/#{date_string}"

        unless Dir.exist?(new_dir)
          FileUtils.mkdir_p(new_dir)
          puts "Created new directory: #{new_dir}"
        end

        begin
          FileUtils.mv(file, new_dir)
          puts "Moved file: #{file} to #{new_dir}"
        rescue StandardError => e
          puts "Error moving file: #{file}. Error: #{e.message}"
        end
      end
    end
  end
end

# Wait for all workers to finish
workers.each(&:join)
