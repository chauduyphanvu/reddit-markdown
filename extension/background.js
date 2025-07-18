const defaults = {
  show_upvotes: true,
  show_timestamp: true,
  line_break_between_parent_replies: true,
  show_auto_mod_comment: false,
  reply_depth_max: -1,
  filter_min_upvotes: 0,
  filter_keywords: [],
  filter_authors: []
};

chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  console.log('Message received in background script:', request);
  if (request.action === 'save') {
    chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
      const tab = tabs[0];
      if (tab.url && tab.url.includes('reddit.com')) {
        chrome.storage.sync.get(defaults, function(settings) {
          fetch(tab.url + '.json')
            .then(response => response.json())
            .then(data => {
              const markdown = buildMarkdown(data, settings);
              const url = 'data:text/markdown;charset=utf-8,' + encodeURIComponent(markdown);
              chrome.downloads.download({
                url: url,
                filename: getFilename(data),
                saveAs: true
              });
            })
            .catch(error => console.error('Error fetching or processing post:', error));
        });
      }
    });
  }
});

function getFilename(data) {
  const postData = data[0].data.children[0].data;
  const title = postData.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
  return `${title}.md`;
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
