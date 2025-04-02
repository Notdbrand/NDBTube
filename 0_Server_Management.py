import keyboard
import os
import json
from flask_bcrypt import Bcrypt
import getpass

# Initialize Bcrypt instance (no Flask app is needed just for hashing)
bcrypt = Bcrypt()

settingsPath = "data/settings.json"
settings = {}
browsers = {
    1: "chrome",
    2: "firefox",
    3: "edge",
    4: "safari",
    5: "opera",
    6: "brave"
}
video_quality_options = [
    {"resolution": "144", "fps": "15", "bitrate": "250"},
    {"resolution": "240", "fps": "20", "bitrate": "400"},
    {"resolution": "360", "fps": "24", "bitrate": "700"},
    {"resolution": "480", "fps": "30", "bitrate": "1000"},
    {"resolution": "720", "fps": "30", "bitrate": "1500"},
    {"resolution": "720", "fps": "60", "bitrate": "2500"},
    {"resolution": "1080", "fps": "30", "bitrate": "3000"},
    {"resolution": "1080", "fps": "60", "bitrate": "5000"},
    {"resolution": "1440", "fps": "60", "bitrate": "8000"}
]

def create_user():
    print("\nCreate user")
    username = input("Enter a username: ")
    password = getpass.getpass("Enter a password: ")
    password_confirm = getpass.getpass("Confirm your password: ")

    if password != password_confirm:
        print("Passwords do not match. Please try again.")
        return create_user()

    print("\nWhat will this account be used on?")
    print("1] Modern Browser (Default)")
    print("2] Legacy Browser")
    print("3] iOS 6 app (WIP)")
    try:
        preferred_access = int(input("Enter number: "))
        if preferred_access >= 2:
            preferred_access = "legacy"
        else:
            preferred_access = "modern"
    except:
        preferred_access = "modern"
        
    print("\nDo you want light or dark mode?")
    print("1] Light Mode (Default)")
    print("2] Dark Mode")
    try:
        theme_mode = int(input("Enter number: "))
        if theme_mode >= 2:
            theme_mode = "dark"
        else:
            theme_mode = "light"
    except:
        theme_mode = "light"
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user_data = {
        "username": username,
        "password": hashed_password,
        "theme_mode": theme_mode,
        "modern_theme": theme_mode,
        "user_theme": ["#121212", "#E0E0E0", "#1A1A1A", "#AA00FF", "#2E2E2E", "#39FF14", "#FFC107", "#333333", "#BF00FF", "rgba(0, 0, 0, 0.7)", "True"],
        "access_type": preferred_access
    }

    users_db_path = "data/users.json"
    if not os.path.exists(users_db_path):
        users_db = {}
    else:
        with open(users_db_path, "r") as f:
            users_db = json.load(f)

    if username in users_db:
        print("Username already exists. Try a different one.")
        return

    users_db[username] = user_data
    os.makedirs(os.path.dirname(users_db_path), exist_ok=True)
    with open(users_db_path, "w") as f:
        json.dump(users_db, f, indent=4)

    user_history_path = f"data/History/{username}_history.json"
    os.makedirs(os.path.dirname(user_history_path), exist_ok=True)
    with open(user_history_path, "w") as f:
        json.dump([], f, indent=4)

    print(f"User '{username}' created successfully!")

def check_existing_file():
    if os.path.exists(settingsPath):
        print("Server files found:")
        print("1] Erase and continue to setup")
        print("2] Add user")
        print("3] Cancel")

        while True:
            try:
                choice = int(input("Enter number: "))
                if choice == 1:
                    print("Erasing all data...")
                    for root, dirs, files in os.walk("data", topdown=False):
                        for name in files:
                            os.remove(os.path.join(root, name))
                        for name in dirs:
                            os.rmdir(os.path.join(root, name))
                    print("All data removed.")
                    break
                elif choice == 2:
                    print("Adding new user...")
                    create_user()
                    exit()
                elif choice == 3:
                    print("\nOperation cancelled.")
                    print("Press SPACE to exit...")
                    keyboard.wait("space")
                    exit()
                else:
                    print("Invalid input. Enter 1, 2, or 3.")
            except ValueError:
                print("Invalid input. Enter 1, 2, or 3.")

def saveSettings(settings):
    os.makedirs(os.path.dirname(settingsPath), exist_ok=True)
    with open(settingsPath, "w") as f:
        json.dump(settings, f, indent=4)
    print("Settings saved to", settingsPath)

# Start
check_existing_file()
print("\nWelcome to the NDBTube setup script!\n")
print("Step 1:")
print("When using yt-dlp, cookies are recommended to stop youtube blocking you.")
print("1] Use cookies from your browser")
print("2] Continue without cookies")

while True:
    try:
        choice = int(input("Enter number: "))
        if choice == 1:
            print("\nSelect your browser with Youtube cookies:")
            for num, browser in browsers.items():
                print(f"{num}] {browser.capitalize()}")
            print("0] Cancel")
            
            while True:
                browser_choice = int(input("Enter number for browser: "))
                if browser_choice == 0:
                    print("\nBrowser selection cancelled.")
                    settings["cookie_option"] = "none"
                    settings["cookie_value"] = None
                    break
                elif browser_choice in browsers:
                    settings["cookie_option"] = "browser"
                    settings["cookie_value"] = browsers[browser_choice]
                    break
                else:
                    print("Invalid browser selection. Try again.")
            if settings["cookie_option"] == "browser":
                break
        elif choice == 2:
            settings["cookie_option"] = "none"
            settings["cookie_value"] = None
            print("Continuing without cookies.")
            break
        else:
            print("Invalid input. Enter 1 or 2.")
    except ValueError:
        print("Invalid input. Enter 1 or 2.")

if settings["cookie_option"] == "browser":
    print(f"Using cookies from browser: {settings['cookie_value']}")
else:
    print("No cookies will be used.")

print("\nStep 2:")
print("Choose a max video quality preset:")
for i, option in enumerate(video_quality_options, start=1):
    print(f"{i}] {option['resolution']}p @ {option['fps']} FPS, {option['bitrate']}kbps")
print(f"{len(video_quality_options)+1}] Set custom video quality")

while True:
    try:
        choice = int(input("Enter number for quality option: "))
        if 1 <= choice <= len(video_quality_options):
            selected_option = video_quality_options[choice - 1]
            settings["video_quality"] = selected_option
            print(f"Selected: {selected_option['resolution']}p @ {selected_option['fps']} FPS, {selected_option['bitrate']}kbps")
            break
        elif choice == len(video_quality_options)+1:
            print("\nCustom quality selected:")
            print("Note: Only enter the vertical resolution and don't include 'p'")
            resolution = int(input("Enter custom resolution: "))
            print("Note: Only enter the value and don't include 'fps'")
            fps = int(input("Enter custom FPS: "))
            print("Note: Enter value in kbps and don't include 'kbps'")
            bitrate = int(input("Enter custom bitrate: "))
            settings["video_quality"] = {"resolution": resolution, "fps": fps, "bitrate": bitrate}
            print(f"Custom quality set: {resolution}p @ {fps} FPS, {bitrate}kbps")
            break
        else:
            print(f"Invalid option. Please select between 1 and {len(video_quality_options)+1}.")
    except ValueError:
        print("Invalid input. Enter a number.")

print("\nStep 3: Security and User Options")
print("1] No login required")
print("2] Login required")

while True:
    try:
        security_choice = int(input("Enter number: "))
        if security_choice == 1:
            settings["security"] = "no_login"
            print("No login required.")
            break
        elif security_choice == 2:
            settings["security"] = "login_required"
            print("Login required.")
            create_user()
            break
        else:
            print("Invalid option. Enter 1 or 2.")
    except ValueError:
        print("Invalid input. Enter 1 or 2.")
        
print("\nStep 4: Download members only content? (You'll need to be a member for each channel that has exclusive content)")
print("1] Skip members only content")
print("2] Download members only content")

while True:
    try:
        members_choice = int(input("Enter number: "))
        if members_choice == 1:
            settings["ignore_member_only"] = 1
            break
        elif members_choice == 2:
            settings["ignore_member_only"] = 0
            break
        else:
            print("Invalid option. Enter 1 or 2.")
    except ValueError:
        print("Invalid input. Enter 1 or 2.")

# Save settings to JSON
saveSettings(settings)

print("\nSetup Complete!")
print("Run script again for other options.")
print("Press SPACE to exit...")
keyboard.wait("space")