document.addEventListener('DOMContentLoaded', function() {
  const saveButton = document.getElementById('save-button');
  const statusDiv = document.getElementById('status');

  saveButton.addEventListener('click', function() {
    statusDiv.textContent = 'Saving...';
    saveButton.disabled = true;

    chrome.runtime.sendMessage({ action: 'save' }, function(response) {
      if (chrome.runtime.lastError) {
        // Handle errors from chrome.runtime.sendMessage itself
        statusDiv.textContent = 'Error: Could not connect to the extension.';
        console.error(chrome.runtime.lastError.message);
        saveButton.disabled = false;
        return;
      }

      if (response && response.success) {
        statusDiv.textContent = 'Post saved!';
      } else {
        statusDiv.textContent = response.error || 'An unknown error occurred.';
      }
      saveButton.disabled = false;
    });
  });
});
