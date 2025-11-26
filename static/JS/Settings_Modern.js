/* Show custom theme in real time */
document.addEventListener("DOMContentLoaded", function () {
	if (theme_type === "custom") {
		const root = document.documentElement;
		const colorInputs = {
		base: '--base',
		light_base: '--light',
		interactive: '--interactive',
		border: '--border',
		hover: '--hover',
		text: '--text',
		shadow: '--shadow',
		icon: '--icon'
		};
		for (const [id, cssVar] of Object.entries(colorInputs)) {
			const input = document.getElementById(id);
			if (input) {
				if (id === 'shadow') {
					root.style.setProperty('--shadow', `rgba(0, 0, 0, ${input.value})`);
				} else {
					root.style.setProperty(cssVar, input.value);
				}

				input.addEventListener('input', () => {
					if (id === 'shadow') {
						root.style.setProperty('--shadow', `rgba(0, 0, 0, ${input.value})`);
					} else {
						root.style.setProperty(cssVar, input.value);
					}
				});
			}
		}
	}
});

/* Save custom theme */
function saveCustomTheme() {
	const payload = {
		access_type: document.getElementById("access_type").value,
		modern_theme: "custom",
		base: document.getElementById("base").value,
		text: document.getElementById("text").value,
		light_base: document.getElementById("light_base").value,
		interactive: document.getElementById("interactive").value,
		border: document.getElementById("border").value,
		hover: document.getElementById("hover").value,
		shadow: document.getElementById("shadow").value,
		icon: document.getElementById("icon").value
	};

	fetch("/api/settings/save_theme", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload)
	}).then(res => {
		if (res.ok) location.reload();
	});
}