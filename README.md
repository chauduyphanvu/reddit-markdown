# reddit-markdown

## Introduction
This Ruby script saves the content of a Reddit post into a Markdown file for easy reading, sharing, and archiving.

## Usage
1. **Install Ruby on your computer**
    * https://www.ruby-lang.org/en/documentation/installation/
2. **Download the script and save it to a folder**
3. **Open a terminal**
4. **Run the script with the following command:**
    * `ruby reddit-markdown.rb`
    * If you call the script from a different folder, you need to specify the path to the script
        * `ruby /path/to/reddit-markdown.rb`
    * Tip: You can rename the script to anything and place it anywhere you want
5. **Enter the link to the Reddit post you want to save**
6. **Enter the path where you want to save the Markdown file**. 
    * Leave blank to save in the same folder (where you called the script from)

## Advantages
* **Open source, and free**
* **No authentication/sign-in of any kind needed**
	* Publicly available data. Safe and no security concerns
* **Look and feel similar to browsing Reddit on desktop web**
* **Supports both text and multimedia posts**
* **Runs anywhere Ruby runs**
	* Ruby is cross-platform
	* Core logic is platform-agnostic so it can be translated into any other programming languages to run anywhere
* **Markdown for universality**

## Limitations
* **Only 1 post at a time**
	* Each time you run this script, you are saving only content from 1 reddit.com link.
	* However, it's trivial to write your own script that calls this script consecutively with a set of links.
* **Only replies that are visible by default on the web are saved**
	* Reddit hides a subset of replies based on upvotes that you can manually click to show. Those won't be saved by this script.
* **Only supported on desktop**
	* But you could remote session from a phone to run the script
* **Need Ruby installed first**
* **Personal side project with limited bug fixes and features past the initial release**
	* Pull requests are welcome