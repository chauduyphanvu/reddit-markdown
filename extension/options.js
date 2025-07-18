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

// Saves options to chrome.storage
function save_options() {
  const settings = {
    show_upvotes: document.getElementById('show_upvotes').checked,
    show_timestamp: document.getElementById('show_timestamp').checked,
    line_break_between_parent_replies: document.getElementById('line_break_between_parent_replies').checked,
    show_auto_mod_comment: document.getElementById('show_auto_mod_comment').checked,
    reply_depth_max: parseInt(document.getElementById('reply_depth_max').value, 10),
    filter_min_upvotes: parseInt(document.getElementById('filter_min_upvotes').value, 10),
    filter_keywords: document.getElementById('filter_keywords').value.split(',').map(s => s.trim()).filter(Boolean),
    filter_authors: document.getElementById('filter_authors').value.split(',').map(s => s.trim()).filter(Boolean),
  };

  chrome.storage.sync.set(settings, function() {
    // Update status to let user know options were saved.
    const status = document.getElementById('status');
    status.textContent = 'Options saved.';
    setTimeout(function() {
      status.textContent = '';
    }, 750);
  });
}

// Restores select box and checkbox state using the preferences
// stored in chrome.storage.
function restore_options() {
  chrome.storage.sync.get(defaults, function(items) {
    document.getElementById('show_upvotes').checked = items.show_upvotes;
    document.getElementById('show_timestamp').checked = items.show_timestamp;
    document.getElementById('line_break_between_parent_replies').checked = items.line_break_between_parent_replies;
    document.getElementById('show_auto_mod_comment').checked = items.show_auto_mod_comment;
    document.getElementById('reply_depth_max').value = items.reply_depth_max;
    document.getElementById('filter_min_upvotes').value = items.filter_min_upvotes;
    document.getElementById('filter_keywords').value = items.filter_keywords.join(', ');
    document.getElementById('filter_authors').value = items.filter_authors.join(', ');
  });
}

document.addEventListener('DOMContentLoaded', restore_options);
document.getElementById('save').addEventListener('click', save_options);
