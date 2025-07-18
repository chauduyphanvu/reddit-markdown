importScripts('jszip.min.js');

const defaults = {
  show_upvotes: true,
  show_timestamp: true,
  line_break_between_parent_replies: true,
  show_auto_mod_comment: false,
  reply_depth_max: -1,
  enable_media_downloads: true,
  filter_min_upvotes: 0,
  filter_keywords: [],
  filter_authors: []
};

chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === 'save') {
    chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
      const tab = tabs[0];
      if (!tab.url || !tab.url.includes('reddit.com')) {
        sendResponse({ success: false, error: 'Not on a Reddit page.' });
        return;
      }

      chrome.storage.sync.get(defaults, function(settings) {
        fetch(tab.url + '.json')
          .then(response => {
            if (!response.ok) {
              throw new Error(`Network response was not ok: ${response.statusText}`);
            }
            return response.json();
          })
          .then(async (data) => {
            const postData = data[0].data.children[0].data;
            let mediaUrls = [];

            if (settings.enable_media_downloads) {
                // --- Media Detection Logic ---
                // 1. Image Galleries
                if (postData.is_gallery) {
                    const galleryItems = postData.gallery_data.items;
                    const mediaMetadata = postData.media_metadata;
                    if (galleryItems && mediaMetadata) {
                        galleryItems.forEach(item => {
                            const mediaId = item.media_id;
                            const meta = mediaMetadata[mediaId];
                            if (meta && meta.e === 'Image') {
                                mediaUrls.push(meta.s.u.replace(/&amp;/g, '&'));
                            }
                        });
                    }
                }
                // 2. Videos and GIFs
                else if (postData.is_video) {
                    mediaUrls.push(postData.media.reddit_video.fallback_url);
                }
                // 3. Simple Image Link
                else if (postData.post_hint === 'image') {
                    mediaUrls.push(postData.url);
                }
            }

            const markdown = buildMarkdown(data, settings);

            if (mediaUrls.length > 0) {
                // --- ZIP Creation Logic ---
                const zip = new JSZip();
                zip.file(`${getFilename(data, false)}.md`, markdown);
                const mediaFolder = zip.folder("media");

                const mediaPromises = mediaUrls.map(url => 
                    fetch(url)
                        .then(res => res.blob())
                        .then(blob => {
                            const filename = url.split('/').pop().split('?')[0];
                            mediaFolder.file(filename, blob);
                        })
                );

                await Promise.all(mediaPromises);

                zip.generateAsync({ type: "blob" }).then(function(content) {
                    const reader = new FileReader();
                    reader.onload = function (e) {
                        chrome.downloads.download({
                            url: e.target.result,
                            filename: `${getFilename(data, false)}.zip`,
                            saveAs: true
                        }, () => sendResponse({ success: true }));
                    };
                    reader.readAsDataURL(content);
                });

            } else {
                // --- Fallback to single file download ---
                const url = 'data:text/markdown;charset=utf-8,' + encodeURIComponent(markdown);
                chrome.downloads.download({
                    url: url,
                    filename: getFilename(data, true),
                    saveAs: true
                }, (downloadId) => {
                    if (chrome.runtime.lastError) {
                        sendResponse({ success: false, error: 'Failed to download file.' });
                    } else {
                        sendResponse({ success: true });
                    }
                });
            }
          })
          .catch(error => {
            console.error('Error fetching or processing post:', error);
            sendResponse({ success: false, error: 'Failed to fetch post data.' });
          });
      });
    });
    return true; // To allow async sendResponse
  }
});

function getFilename(data, includeExtension) {
    const postData = data[0].data.children[0].data;
    const title = postData.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    return includeExtension ? `${title}.md` : title;
}

function buildMarkdown(data, settings) {
  const postData = data[0].data.children[0].data;
  const repliesData = data[1].data.children;

  let markdown = ``;

  // Post Header
  let upvotes = '';
  if (settings.show_upvotes) {
    upvotes = `| ⬆️ ${postData.ups}`;
  }
  markdown += `**${postData.subreddit_name_prefixed}** | Posted by u/${postData.author} ${upvotes}\n`;
  markdown += `## ${postData.title}\n`;
  markdown += `[Original Post](${postData.url})\n\n`;

  // Post Body
  if (postData.selftext) {
    markdown += `> ${postData.selftext.replace(/\n/g, '\n> ')}\n\n`;
  }
  
  // Media Links in Markdown
  if (settings.enable_media_downloads) {
    if (postData.is_gallery || postData.post_hint === 'image') {
        markdown += '### Media\n';
        const mediaUrls = getMediaUrls(postData); // Helper function to get URLs
        mediaUrls.forEach(url => {
            const filename = url.split('/').pop().split('?')[0];
            markdown += `![media](./media/${filename})\n`;
        });
        markdown += '\n';
    } else if (postData.is_video) {
        const videoUrl = postData.media.reddit_video.fallback_url;
        const filename = videoUrl.split('/').pop().split('?')[0];
        markdown += `### Video\n<video controls src="./media/${filename}"></video>\n\n`;
    }
  }

  // Replies
  markdown += `💬 ~ ${postData.num_comments} replies\n---\n\n`;
  repliesData.forEach(reply => {
    if (reply.kind === 't1') { // t1 denotes a comment
      if (settings.show_auto_mod_comment || reply.data.author !== 'AutoModerator') {
        markdown += renderReply(reply.data, 0, postData.author, settings);
        if (settings.line_break_between_parent_replies) {
            markdown += '---\n\n';
        }
      }
    }
  });

  return markdown;
}

function getMediaUrls(postData) {
    let urls = [];
    if (postData.is_gallery) {
        const galleryItems = postData.gallery_data.items;
        const mediaMetadata = postData.media_metadata;
        if (galleryItems && mediaMetadata) {
            galleryItems.forEach(item => {
                const mediaId = item.media_id;
                const meta = mediaMetadata[mediaId];
                if (meta && meta.e === 'Image') {
                    urls.push(meta.s.u.replace(/&amp;/g, '&'));
                }
            });
        }
    } else if (postData.post_hint === 'image') {
        urls.push(postData.url);
    }
    return urls;
}


function renderReply(replyData, depth, postAuthor, settings) {
  // Filtering
  if (replyData.score < settings.filter_min_upvotes) return '';
  if (settings.filter_authors.includes(replyData.author)) return '';
  for (const keyword of settings.filter_keywords) {
    if (replyData.body.toLowerCase().includes(keyword.toLowerCase())) return '';
  }

  let replyMarkdown = ``;

  const indent = '\t'.repeat(depth);
  let author = replyData.author;
  if (author === postAuthor) {
    author += ' (OP)';
  }

  let upvotes = '';
  if (settings.show_upvotes) {
    upvotes = `| ⬆️ ${replyData.score}`;
  }
  let timestamp = '';
  if (settings.show_timestamp) {
      const d = new Date(replyData.created_utc * 1000);
      timestamp = `| _${d.toLocaleString()}_`;
  }

  replyMarkdown += `${indent}* **${author}** ${upvotes} ${timestamp}\n\n`;
  replyMarkdown += `${indent}\t${replyData.body.replace(/\n/g, `\n${indent}\t`)}\n\n`;

  if (settings.reply_depth_max === -1 || depth < settings.reply_depth_max) {
      if (replyData.replies && replyData.replies.data) {
        replyData.replies.data.children.forEach(childReply => {
          if (childReply.kind === 't1') {
            replyMarkdown += renderReply(childReply.data, depth + 1, postAuthor, settings);
          }
        });
      }
  }

  return replyMarkdown;
}
