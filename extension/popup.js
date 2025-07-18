document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('save-button').addEventListener('click', function() {
    console.log('Save button clicked, sending message to background script.');
    chrome.runtime.sendMessage({ action: 'save' });
  });
});
