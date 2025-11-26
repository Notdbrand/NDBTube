function saveDownloadSettings() {
	var resolution = document.getElementById("resolution").value;
	var fps = document.getElementById("fps").value;

	var payload = {
		resolution: resolution,
		fps: fps
	};

	var xhr = new XMLHttpRequest();
	xhr.open("POST", "/api/settings/save_download_settings", true);
	xhr.setRequestHeader("Content-Type", "application/json");

	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				alert("Settings saved successfully!");
				location.reload();
			} else {
				alert("Failed to save settings. Please try again.");
			}
		}
	};

	xhr.send(JSON.stringify(payload));
}

/* Save password for current user */
function savePassword() {
	var current_password = document.getElementById("current").value;
	var new_password = document.getElementById("new").value;
	var confirm_password = document.getElementById("confirm").value;

	var payload = {
		username: username,
		current_password: current_password,
		new_password: new_password,
		confirm_password: confirm_password
	};

	var xhr = new XMLHttpRequest();
	xhr.open("POST", "/api/settings/password", true);
	xhr.setRequestHeader("Content-Type", "application/json");

	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				alert("Password Changed successfully!");
				location.reload();
			} else {
				try {
					var data = JSON.parse(xhr.responseText);
					alert(data.message || "Failed to change password.");
				} catch (e) {
					alert("Failed to change password.");
				}
			}
		}
	};

	xhr.send(JSON.stringify(payload));
}
	
/* Scan all the locations for new channels and videos */	
function updateArchive() {
	var payload = {
		location: document.getElementById("location").value
	};
	
	var xhr = new XMLHttpRequest();
	xhr.open("POST", "/api/settings/update_archive", true);
	xhr.setRequestHeader("Content-Type", "application/json");

	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				alert("Archive Updated successfully!");
				location.reload();
			} else {
				alert("Failed to update archive. Please try again.");
			}
		}
	};

	xhr.send(JSON.stringify(payload));
}

/* Add new location */
function saveLocationSettings() {
	var payload = {
		location: document.getElementById("location").value
	};
	var xhr = new XMLHttpRequest();
	xhr.open("POST", "/api/settings/save_location_settings", true);
	xhr.setRequestHeader("Content-Type", "application/json");

	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				alert("Location saved successfully!");
				location.reload();
			} else {
				alert("Failed to save location. Please try again.");
			}
		}
	};

	xhr.send(JSON.stringify(payload));
}

/* Remove a location */
function removeLocationSetting(x) {
	var payload = {
		location: x
	};

	var xhr = new XMLHttpRequest();
	xhr.open("POST", "/api/settings/remove_location_setting", true);
	xhr.setRequestHeader("Content-Type", "application/json");

	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				alert("Location removed successfully!");
				location.reload();
			} else {
				alert("Failed to remove location. Please try again.");
			}
		}
	};

	xhr.send(JSON.stringify(payload));
}

/* Apply access and theme settings */
function applySettings() {
	var payload = {
		access_type: document.getElementById("access_type").value,
		modern_theme: document.getElementById("modern_theme").value
	};

	var xhr = new XMLHttpRequest();
	xhr.open("POST", "/api/settings/apply", true);
	xhr.setRequestHeader("Content-Type", "application/json");

	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				alert("Settings saved successfully!");
				location.reload();
			} else {
				alert("Failed to save settings. Please try again.");
			}
		}
	};

	xhr.send(JSON.stringify(payload));
}
