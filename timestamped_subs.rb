require 'fileutils'
require 'date'

# This script will organize your Reddit posts into directories based on the timestamp of the post. Doing that helps you find posts by date more easily and also helps you reduce the number of files in a single directory.
# For example, if you have a saved post with a timestamp of 2020-01-01 12:00:00, it will be moved to a directory named 2020-01-01.

# Edit this to the base directory where you downloaded your Reddit posts.
# Note: This base directory path is relative to the directory where you run this script.
base_dir = '../Downloads/Reddit/'

Dir.glob("#{base_dir}/**/*.md") do |file|
  puts "Processing file: #{file}"

  if File.dirname(file).match?(/\d{4}-\d{2}-\d{2}/)
    puts "File is already in a timestamped directory: #{file}"
    next
  end
  
  content = File.read(file)
  timestamp = content.match(/\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\)/)

  if timestamp.nil?
    puts "No timestamp found in file: #{file}. Skipping."
  else
    date = Date.parse(timestamp[0][1...-1])
    date_string = date.strftime('%Y-%m-%d')

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
