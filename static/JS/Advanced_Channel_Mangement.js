/* Update Selected */
document.getElementById('update-selected').addEventListener('click', function () {
	var update_type = document.getElementById('update_type').value;
	var selectedUploaderIds = [update_type];

	var checkboxes = document.querySelectorAll('.update-channel-checkbox');
	checkboxes.forEach(function (checkbox) {
		if (checkbox.checked) {
			var uploaderId = checkbox.getAttribute('data-uploader');
			if (uploaderId) {
				selectedUploaderIds.push(uploaderId);
			}
		}
	});

	if (selectedUploaderIds.length === 1) {
		alert('No channels selected.');
		return;
	}

	var xhr = new XMLHttpRequest();
	xhr.open('POST', '/ChannelManagement/UpdateSelected', true);
	xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
	xhr.send(JSON.stringify(selectedUploaderIds));
});

/* Update All */
document.getElementById('update-all').addEventListener('click', function () {
	var update_type = document.getElementById('update_type').value;
	var allUploaderIds = [update_type];
	var xhr = new XMLHttpRequest();
	xhr.open('POST', '/ChannelManagement/UpdateAll', true);
	xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
	xhr.send(JSON.stringify(allUploaderIds));
});

/* Remove Channel Request */
document.getElementById('delete-form').addEventListener('submit', function (e) {
	e.preventDefault();

	var select = document.getElementById('channel_delete');
	var selectedOption = select.selectedOptions[0];

	var uploader = selectedOption.getAttribute('uploader');
	var uploader_id = selectedOption.getAttribute('uploader_id');
	var confirm = document.getElementById('confirm').value;

	var payload = [
		{
			uploader: uploader,
			uploader_id: uploader_id,
			confirm: confirm
		}
	];

	var xhr = new XMLHttpRequest();
	xhr.open('POST', '/ChannelManagement/Delete', true);
	xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			try {
				var data = JSON.parse(xhr.responseText);
				if (data.success) {
					alert('Channel Deleted');
				} else {
					alert('Deletion failed: ' + data.error);
				}
			} catch (err) {
				alert('Unexpected server response.');
			}
		}
	};
	xhr.send(JSON.stringify(payload));
});
