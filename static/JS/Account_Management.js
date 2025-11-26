/* Create a new account */
function newAccount() {
	var username = document.getElementById("user").value;
	var password = document.getElementById("password").value;
	var role = document.getElementById("role").value;
	var confirm_password = document.getElementById("confirm").value;
	var access_type = document.getElementById("access_type").value;
	var modern_theme = document.getElementById("modern_theme").value;

	var payload = {
		username: username,
		password: password,
		role: role,
		confirm_password: confirm_password,
		access_type: access_type,
		modern_theme: modern_theme
	};

	var xhr = new XMLHttpRequest();
	xhr.open("POST", "/AccountManagement/0/new_account", true);
	xhr.setRequestHeader("Content-Type", "application/json");

	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				alert("Account Created!");
				location.reload();
			} else {
				try {
					var data = JSON.parse(xhr.responseText);
					alert(data.message || "Failed to create account.");
				} catch (e) {
					alert("Failed to create account.");
				}
			}
		}
	};

	xhr.send(JSON.stringify(payload));
}

/* Update the role of the selected user */
function saveRole() {
	var new_role = document.getElementById("role").value;

	var payload = {
		username: username,
		new_role: new_role
	};

	var xhr = new XMLHttpRequest();
	xhr.open("POST", '/AccountManagement/{{ user["id"] }}/role', true);
	xhr.setRequestHeader("Content-Type", "application/json");

	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				alert("Role Changed.");
				location.reload();
			} else {
				try {
					var data = JSON.parse(xhr.responseText);
					alert(data.message || "Failed to change role.");
				} catch (e) {
					alert("Failed to change role.");
				}
			}
		}
	};

	xhr.send(JSON.stringify(payload));
}

/* Update the password of the selected user */
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
	xhr.open("POST", '/AccountManagement/{{ user["id"] }}/password', true);
	xhr.setRequestHeader("Content-Type", "application/json");

	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				alert("Password Changed.");
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

/* Delete the selected user */
function deleteAccount() {
	var deletepassword = document.getElementById("deletepassword").value;

	var payload = {
		username: username,
		deletepassword: deletepassword
	};

	var xhr = new XMLHttpRequest();
	xhr.open("POST", '/AccountManagement/{{ user["id"] }}/deleteaccount', true);
	xhr.setRequestHeader("Content-Type", "application/json");

	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				alert("Account Removed.");
				window.location.href = '/AccountManagement';
			} else {
				try {
					var data = JSON.parse(xhr.responseText);
					alert(data.message || "Failed to remove account.");
				} catch (e) {
					alert("Failed to remove account.");
				}
			}
		}
	};

	xhr.send(JSON.stringify(payload));
}