from flask import Flask, render_template, request, abort, jsonify, session, redirect, url_for, send_from_directory
import json
import random
import os
import bcrypt
import secrets
from datetime import datetime
import subprocess
import threading
import shutil
import uuid

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

download_lock = threading.Lock()
global_status_string = "Idle"
current_process = None

def channel_download_starter(data, type):
    global global_status_string
    if type == 1:
        global_status_string = "Starting Single Channel Download."
        return start_channel_download(data)
    elif type == 2:
        global_status_string = "Starting Update for Selected Channels."
        return start_channel_download(data, is_update=True)
    elif type == 3:
        global_status_string = "Starting Update for All Channels."
        all_channels = load_channels()
        uploader_ids = [ch["uploader_id"] for ch in all_channels]
        data = data + uploader_ids
        return start_channel_download(data, is_update=True)
    return "Unknown operation"

def start_channel_download(data, is_update=False):
    global current_process
    global global_status_string

    if not download_lock.acquire(blocking=False):
        print("Download already in progress.")
        return "Download already in progress."

    def run_download(channel_url, include_videos, include_shorts, include_streams, quick_update=False, location=0):
        global current_process

        input_data = f"{channel_url}\n{include_videos}\n{include_shorts}\n{include_streams}\n{quick_update}\n{location}\n"
        current_process = subprocess.Popen(
            ["python", "1_Channel_Download.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        current_process.stdin.write(input_data)
        current_process.stdin.flush()
        current_process.stdin.close()

        for line in current_process.stdout:
            print(f"[Downloader] {line}", end="")
        current_process.stdout.close()
        current_process.wait()

    def update_mode(uploader_ids):
        quick_update = uploader_ids.pop(0)
        all_channels = load_channels()
        lookup = {ch["uploader_id"]: ch for ch in all_channels}
        total = len(uploader_ids)

        for idx, uploader_id in enumerate(uploader_ids):
            ch = lookup.get(uploader_id)
            if not ch:
                print(f"Channel {uploader_id} not found. Skipping.")
                continue

            global global_status_string
            global_status_string = f"Updating Channel: {ch['uploader']} ({idx}/{total})"

            channel_url = ch["channel_URL"]
            sections = ch.get("to_download_sections", [])
            include_videos = "videos" in [s.lower() for s in sections]
            include_shorts = "shorts" in [s.lower() for s in sections]
            include_streams = "streams" in [s.lower() for s in sections]
            location = ch["location"]
            server_settings = load_settings()
            download_locations = server_settings["locations"]
            location_index = download_locations.index(location)
            run_download(channel_url, str(include_videos), str(include_shorts), str(include_streams), str(quick_update), str(location_index))

    try:
        if is_update:
            update_mode(data)
        else:
            entry = data[0]
            channel_url = entry["channel_url"]
            include_videos = str(entry["include_videos"])
            include_shorts = str(entry["include_shorts"])
            include_streams = str(entry["include_streams"])
            location = str(entry["location"])

            global_status_string = f"Downloading: {channel_url}"
            threading.Thread(target=lambda: [run_download(channel_url, include_videos, include_shorts, include_streams, False, location), download_lock.release(), set_idle_status()], daemon=True).start()
            return "Download started."

        threading.Thread(target=lambda: [download_lock.release(), set_idle_status()], daemon=True).start()
        return "Update started."

    except Exception as e:
        download_lock.release()
        global_status_string = "Idle"
        print(f"Error: {e}")
        return f"Error: {e}"

def set_idle_status():
    global global_status_string
    global_status_string = "Idle"

#Basic functions
def load_settings():
    with open("data/settings.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_users():
    with open("data/users.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_user(user_id):
    users = load_users()
    for user_key, user_info in users.items():
        if user_info.get("id") == user_id:
            return user_info
    return None

def get_current_user_access():
    if "user" in session:
        users = load_users()
        user_info = users.get(session["user"], {})
        return user_info.get("access_type", "legacy")
    return "legacy"

def get_current_user_rights():
    if "user" in session:
        users = load_users()
        user_info = users.get(session["user"], {})
        return user_info.get("role", "user")
    return "user"

def update_archive():
    locations = load_settings()["locations"]

    video_files = []
    channel_files = []

    all_videos = []
    all_channels = []

    for base in locations:
        for root, dirs, files in os.walk(base):
            for f in files:
                if f == "All_Videos.json":
                    continue

                full_path = os.path.join(root, f)

                if f.endswith(("_Videos.json", "_Shorts.json", "_Streams.json")):
                    video_files.append((base, full_path))

                if f.endswith("channel.json"):
                    channel_files.append((base, full_path))

    for base, path in video_files:
        with open(path, "r", encoding="utf-8") as f:
            file_videos = json.load(f)

        for video in file_videos:
            new_video = {
                "title": video["title"],
                "video_id": video["video_id"],
                "views": video["views"],
                "uploaddate": video["uploaddate"],
                "duration": video["duration"],
                "uploader": video["uploader"],
                "uploader_id": video["uploader_id"],
                "location": base
            }
            all_videos.append(new_video)

    with open("static/All_Videos.json", "w", encoding="utf-8") as f:
        json.dump(all_videos, f, indent=4)

    for base, path in channel_files:
        with open(path, "r", encoding="utf-8") as f:
            channel = json.load(f)

        new_channel = {
            "uploader": channel["uploader"],
            "uploader_id": channel["uploader_id"],
            "subscriber_count": channel["subscriber_count"],
            "total_views": channel["total_views"],
            "channel_videos": channel["video_count"],
            "channel_URL": f"https://youtube.com/{channel['uploader_id']}",
            "downloaded_sections": channel["downloaded_sections"],
            "to_download_sections": channel["downloaded_sections"],
            "location": base,
            "last_checked": channel["last_checked"],
        }

        all_channels.append(new_channel)

    with open("static/channels.json", "w", encoding="utf-8") as f:
        json.dump(all_channels, f, indent=4)

@app.before_request
def first_setup():
    if not os.path.isfile("data/users.json") and request.endpoint != "setup":
        return redirect(url_for("setup"))
        
def check_login():
    settings = load_settings()
    if settings.get("security") == "login_required" and "user" not in session:
        return redirect(url_for("login"))

@app.before_request
def require_login():
    if os.path.isfile("data/users.json"):
        if request.endpoint not in ["login", "logout", "legacy_app", "legacy_home", "legacy_channels", "static"]:
            login_redirect = check_login()
            if login_redirect:
                return login_redirect

@app.before_request
def check_user_still_exists():
    if os.path.isfile("data/users.json"):
        user = session.get("user")
        users = load_users()
        if user and user not in users:
            session.clear()
            return redirect(url_for("login"))
        
def load_all_videos():
    all_videos = "static/All_Videos.json"
    if not os.path.exists(all_videos):
        return []
    with open(all_videos, "r", encoding="utf-8") as f:
        return json.load(f)

def load_channels():
    all_channels = "static/channels.json"
    if not os.path.exists(all_channels):
        return []
    with open(all_channels, "r", encoding="utf-8") as f:
        return json.load(f)

def load_channel_content(channel, type):
    server_settings = load_settings()
    download_locations = server_settings["locations"]
    for download_location in download_locations:
        channel_path = f"{download_location}/channels/{channel}/{channel}_{type}.json"
        if os.path.exists(channel_path):
            with open(channel_path, "r", encoding="utf-8") as f:
                return json.load(f)
    return None

def load_channel_playlist(channel, playlist_id):
    playlists = load_channel_content(channel, "Playlists")
    for playlist in playlists:
        if playlist.get("playlist_id") == playlist_id:
            return playlist
    return []

def load_channel_playlist_videos(channel, playlist_id):
    playlists = load_channel_content(channel, "Playlists")
    for playlist in playlists:
        if playlist.get("playlist_id") == playlist_id:
            return playlist.get("videos", [])
    return []

def load_channel_info(channel):
    server_settings = load_settings()
    download_locations = server_settings["locations"]
    for download_location in download_locations:
        channel_path = f"{download_location}/channels/{channel}/channel.json"
        if os.path.exists(channel_path):
            with open(channel_path, "r", encoding="utf-8") as f:
                return json.load(f)

    return None

def load_user_history(user):
    with open(f"data/history/{user}_history.json", "r", encoding="utf-8") as f:
        return json.load(f)

def make_new_account(data, setup=False):
    username = data.get("username")
    password = data.get("password")
    confirm_password = data.get("confirm_password")
    role = data.get("role")
    preferred_access = data.get("access_type")
    theme_mode = data.get("modern_theme")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    if username == '':
        return jsonify({"success": False, "message": "No username provided."}), 400
    if password == '':
        return jsonify({"success": False, "message": "No password provided."}), 400
    
    if password != confirm_password:
        return jsonify({"success": False, "message": "Password don't match."}), 400
    users_db_path = "data/users.json"
    if not os.path.exists(users_db_path):
        users_db = {}
    else:
        with open(users_db_path, "r") as f:
            users_db = json.load(f)
    if username in users_db:
        return jsonify({"success": False, "message": "Username already exists. Try a different one."}), 400

    user_data = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password": hashed_password,
        "role": role,
        "access_type": preferred_access,
        "legacy_theme": theme_mode,
        "modern_theme": theme_mode,
        "user_theme": [
            "#121212", "#ffffff", "#1a1a1a", "#ff0000",
            "custom", "custom", "custom", "#ff0000",
            "#ffffff", "0.7", "#ffffff"
        ]
    }

    users_db[username] = user_data
    os.makedirs(os.path.dirname(users_db_path), exist_ok=True)
    with open(users_db_path, "w") as f:
        json.dump(users_db, f, indent=4)
    user_history_path = f"data/History/{username}_history.json"
    os.makedirs(os.path.dirname(user_history_path), exist_ok=True)
    with open(user_history_path, "w") as f:
        json.dump([], f, indent=4)
    if setup:
        return
    return jsonify({"success": True})

def make_settings(data):
    cookies = data.get("cookies")
    download_quality = data.get("download_quality")
    settings = {
        "security": "login_required",
        "ignore_member_only": int(data.get("members_content")),
        "locations": ["static"]
    }
    
    if cookies == "no_cookies":
        settings["cookie_option"] = "none"
        settings["cookie_value"] = "none"
    elif cookies == "custom_cookies":
        settings["cookie_option"] = "browser"
        settings["cookie_value"] = data.get("custom_cookies_value")
    else:
        settings["cookie_option"] = "browser"
        settings["cookie_value"] = cookies
        
    if download_quality == "custom_quality":
        settings["video_quality"] = {"resolution": int(data.get("custom_resolution")), "fps": int(data.get("custom_framerate"))}
    else:
        download_values = download_quality.split()
        settings["video_quality"] = {"resolution": int(download_values[0]), "fps": int(download_values[1])}
    with open("data/settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

# ---------------------------
# Both
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        users = load_users()
        username = request.form.get("username")
        password = request.form.get("password")
        access = request.form.get("access")
        user_info = users.get(username)
        if user_info:
            stored_hash = user_info["password"]
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
                session["user"] = username
                if access == "legacy":
                    users[username]["access_type"] = access
                    with open("data/users.json", "w", encoding="utf-8") as f:
                        json.dump(users, f, indent=4)
                    return redirect(url_for("modern_home"))
                elif access == "modern":
                    users[username]["access_type"] = access
                    with open("data/users.json", "w", encoding="utf-8") as f:
                        json.dump(users, f, indent=4)
                    return redirect(url_for("modern_home"))
                elif access == "default":
                    return redirect(url_for("modern_home"))
                else:
                    error = "Invalid Access Selected"
                    return render_template("1_Login.html", error=error)
                    
        error = "Invalid Credentials"
        return render_template("1_Login.html", error=error)

    return render_template("1_Login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

        
@app.route("/shutdown", methods=["POST"])
def shutdown():
    if get_current_user_rights() != "admin":
        abort(403)
        
    def shutdown_server():
        import time
        time.sleep(2)
        os._exit(0)

    threading.Thread(target=shutdown_server).start()
    return '''
        <script>
            alert("Server is shutting down...");
        </script>
    '''
    
def server_setup(data):
    print(data)
    userdata = {
        "username": data.get("username"),
        "password": data.get("password"),
        "confirm_password": data.get("password"),
        "role": "admin",
        "access_type": data.get("access_type"),
        "modern_theme": data.get("user_theme")
    }
    try:
        make_new_account(userdata, True)
    except:
        return '''
            <script>
                alert("Failed to make account");
            </script>
        '''
    try:
        make_settings(data)
    except:
        return '''
            <script>
                alert("Failed to make settings");
            </script>
        '''
    return '''
        <script>
            alert("Setup Successful!");
        </script>
    '''

@app.route("/setup", methods=["GET", "POST"])
def setup():
    if not os.path.isfile("data/users.json"):
        if request.method == "POST":
            data = request.json
            return server_setup(data)
        return render_template("0_Setup.html")
    return '''
        <script>
            alert("Unauthorised Access");
            window.history.back();
        </script>
    '''

@app.route("/thumbnail/<channel_id>/<video_id>")
def serve_thumbnail(channel_id, video_id):
    server_settings = load_settings()
    download_locations = server_settings["locations"]
    for download_location in download_locations:
        thumbnail_path = f"{download_location}/channels/{channel_id}/thumbnails/{video_id}.jpg"
        if os.path.exists(thumbnail_path):
            return send_from_directory(f"{download_location}/channels/{channel_id}/thumbnails", f"{video_id}.jpg")  
    return send_from_directory("data", "404.jpg")
    
@app.route("/icon/<channel_id>")
def serve_icon(channel_id):
    server_settings = load_settings()
    download_locations = server_settings["locations"]
    for download_location in download_locations:
        icon_path = f"{download_location}/channels/{channel_id}/channel.png"
        if os.path.exists(icon_path):
            return send_from_directory(f"{download_location}/channels/{channel_id}/", f"channel.png")  
    return send_from_directory("data", "404.jpg")
    
@app.route("/banner/<channel_id>")
def serve_banner(channel_id):
    server_settings = load_settings()
    download_locations = server_settings["locations"]
    for download_location in download_locations:
        banner_path = f"{download_location}/channels/{channel_id}/banner.png"
        if os.path.exists(banner_path):
            return send_from_directory(f"{download_location}/channels/{channel_id}/", f"banner.png")  
    return send_from_directory("data", "404.jpg")
    
@app.route("/video/<channel_id>/<video_id>")
def serve_video(channel_id, video_id):
    server_settings = load_settings()
    download_locations = server_settings["locations"]
    for download_location in download_locations:
        video_path = f"{download_location}/channels/{channel_id}/videos/{video_id}.mp4"
        if os.path.exists(video_path):
            return send_from_directory(f"{download_location}/channels/{channel_id}/videos/", f"{video_id}.mp4")

def get_formatted_datetime():
    return datetime.now().strftime("%H:%M %d/%m/%Y")
    
#Theme is locked to account legacy
@app.context_processor
def inject_theme_css():
    if os.path.isfile("data/users.json"):
        theme_css = "Legacy_Light_Mode.css"
        if "user" in session:
            users = load_users()
            user_info = users.get(session["user"], {})
            if user_info.get("legacy_theme", "light") == "dark":
                theme_css = "Legacy_Dark_Mode.css"
        return dict(theme_css=theme_css)
    return dict(theme_css="Legacy_Light_Mode.css")

#Theme is locked to account modern
@app.context_processor
def modern_colours_css():
    if os.path.isfile("data/users.json"):
        colour_css = ["#FFFFFF", "#1F1F1F", "#F5F5F5", "#007BFF", "#E9ECEF", "#28A745", "#FFC107", "#CED4DA", "#000000", "0.3", "#000000"]
        if "user" in session:
            users = load_users()
            user_info = users.get(session["user"], {})
            if user_info.get("modern_theme", "light") == "dark":
                colour_css = ["#121212", "#E0E0E0", "#1E1E1E", "#007BFF", "#2E2E2E", "#28A745", "#FFC107", "#333333", "#FFFFFF", "0.7", "#FFFFFF"]
            elif user_info.get("modern_theme", "light") == "custom":
                colour_css = user_info.get("user_theme")
        return dict(colour_css=colour_css)
    return dict(colour_css=["#FFFFFF", "#1F1F1F", "#F5F5F5", "#007BFF", "#E9ECEF", "#28A745", "#FFC107", "#CED4DA", "#000000", "0.3", "#000000"])

@app.route("/ChannelManagement/save_prefs", methods=["POST"])
def save_channel_prefs():
    if "user" not in session:
        return redirect(url_for("login"))
    data = request.get_json()
    if not data or "prefs" not in data:
        return jsonify(success=False, error="No prefs"), 400
    path = os.path.join("static", "channels.json")
    with open(path, "r", encoding="utf-8") as f:
        channels = json.load(f)

    lookup = { p["uploader_id"]: p for p in data["prefs"] }

    for ch in channels:
        key = ch.get("uploader_id") or ch.get("uploader")
        if key in lookup:
            ch["to_download_sections"] = lookup[key]["to_download_sections"]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4, ensure_ascii=False)

    return jsonify(success=True)

@app.route("/ChannelManagement/Status", methods=["GET"])
def download_status():
    if "user" not in session:
        return redirect(url_for("login"))
    return jsonify(status=global_status_string)

@app.route("/ChannelManagement/SingleDownload", methods=["POST"])
def single_channel_download():
    if "user" not in session:
        return redirect(url_for("login"))
    data = request.get_json()
    print("Single Download")
    print(data)
    result = channel_download_starter(data, 1)
    return jsonify(success=(result == "Download started."), status=result)
    
@app.route("/ChannelManagement/UpdateSelected", methods=["POST"])
def update_selected():
    if "user" not in session:
        return redirect(url_for("login"))
    data = request.get_json()
    print("UpdateSelected")
    print(data)
    channel_download_starter(data, 2)
    return jsonify(success=True)
    
@app.route("/ChannelManagement/UpdateAll", methods=["POST"])
def update_all():
    if "user" not in session:
        return redirect(url_for("login"))
    data = request.get_json()
    print("UpdateAll")
    print(data)
    channel_download_starter(data, 3)
    return jsonify(success=True)
    
@app.route("/ChannelManagement/Delete", methods=["POST"])
def delete_request():
    if "user" not in session:
        return redirect(url_for("login"))
    if get_current_user_rights() != "admin":
        abort(403)
    
    data = request.get_json()
    uploader_to_remove = data[0]["uploader"]
    uploader_id_to_remove = data[0]["uploader_id"]
    confirm = data[0]["confirm"]
    print(data)
    
    if confirm == uploader_to_remove:
        channels = load_channels()
        videos = load_all_videos()
        filtered_channels = [entry for entry in channels if entry["uploader_id"] != uploader_id_to_remove]
        filtered_videos = [entry for entry in videos if entry["uploader_id"] != uploader_id_to_remove]

        with open("static/channels.json", 'w', encoding='utf-8') as f:
            json.dump(filtered_channels, f, indent=4, ensure_ascii=False)
        with open("static/All_Videos.json", 'w', encoding='utf-8') as f:
            json.dump(filtered_videos, f, indent=4, ensure_ascii=False)
        
        shutil.rmtree(f"static/channels/{uploader_id_to_remove}")
        return jsonify(success=True)
    elif uploader_to_remove == "Select a Channel":
        return jsonify(success=False, error="Select a Channel")
    elif confirm != uploader_to_remove:
        return jsonify(success=False, error="Confirmation Failed")
    else:
        return jsonify(success=False)
    
# ---------------------------
# Legacy Browser
# ---------------------------
@app.route("/legacy/")
def legacy_home():
    print(session)
    videos = load_all_videos()
    channels = load_channels()
    random_videos = random.sample(videos, min(18, len(videos)))
    return render_template("/legacy/2_LegacyHome.html", videos=random_videos, channels=channels)

@app.route("/legacy/channels")
def legacy_channels():
    channels = load_channels()
    sort_by = request.args.get("sort", "alpha")
    if sort_by == "alpha":
        channels = sorted(channels, key=lambda x: x["uploader"].lower())
    elif sort_by == "most_videos":
        channels = sorted(channels, key=lambda x: int(x["channel_videos"]), reverse=True)
    return render_template("/legacy/3_LegacyChannelList.html", 
                            channels=channels, sort_by=sort_by,
                            rights=get_current_user_rights())

@app.route("/legacy/<channel_id>")
def legacy_channel_home_page(channel_id):
    channels = load_channels()
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        abort(404)
    channel_videos = load_channel_content(channel_id, "Videos")
    if not channel_videos:
        abort(404)
    recent_videos = channel_videos[0:3]
    channel_info = load_channel_info(channel_id)
    random_channel_videos = random.sample(channel_videos, min(3, len(channel_videos)))
    return render_template("/legacy/7_1_LegacyChannelHome.html",
                           random_videos=random_channel_videos,
                           recent_videos=recent_videos,
                           channel=channel_id[1:],
                           channel_info=channel_info)

def process_channel_videos(channel_videos, sort_by, page, videos_per_page=15):
    if sort_by == "popular":
        channel_videos = sorted(channel_videos, key=lambda x: x["views"], reverse=True)
    elif sort_by == "oldest":
        channel_videos = list(reversed(channel_videos))
    elif sort_by == "leastpopular":
        channel_videos = list(reversed(sorted(channel_videos, key=lambda x: x["views"], reverse=True)))
    start_idx = (page - 1) * videos_per_page
    end_idx = start_idx + videos_per_page
    paginated_videos = channel_videos[start_idx:end_idx]
    total_pages = (len(channel_videos) + videos_per_page - 1) // videos_per_page
    return paginated_videos, total_pages


@app.route("/legacy/<channel_id>/videos")
def legacy_channel_videos_page(channel_id):
    channels = load_channels()
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        abort(404)
    channel_videos = load_channel_content(channel_id, "Videos")
    channel_info = load_channel_info(channel_id)
    if not channel_videos:
        abort(404)
    
    sort_by = request.args.get("sort", "newest")
    page = int(request.args.get("page", 1))
    paginated_videos, total_pages = process_channel_videos(channel_videos, sort_by, page)
    
    return render_template("/legacy/7_2_LegacyChannelVideos.html",
                           videos=paginated_videos,
                           channel=channel_id[1:],
                           channel_info=channel_info,
                           sort_by=sort_by,
                           page=page,
                           total_pages=total_pages)

@app.route("/legacy/<channel_id>/shorts")
def legacy_channel_shorts_page(channel_id):
    channels = load_channels()
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        abort(404)
    channel_shorts = load_channel_content(channel_id, "Shorts")
    channel_info = load_channel_info(channel_id)
    if not channel_shorts:
        abort(404)
    
    sort_by = request.args.get("sort", "newest")
    page = int(request.args.get("page", 1))
    paginated_videos, total_pages = process_channel_videos(channel_shorts, sort_by, page)
    
    return render_template("/legacy/7_3_LegacyChannelShorts.html",
                           videos=paginated_videos,
                           channel=channel_id[1:],
                           channel_info=channel_info,
                           sort_by=sort_by,
                           page=page,
                           total_pages=total_pages)

@app.route("/legacy/<channel_id>/streams")
def legacy_channel_streams_page(channel_id):
    channels = load_channels()
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        abort(404)
    channel_streams = load_channel_content(channel_id, "Streams")
    channel_info = load_channel_info(channel_id)
    if not channel_streams:
        abort(404)
    
    sort_by = request.args.get("sort", "newest")
    page = int(request.args.get("page", 1))
    paginated_videos, total_pages = process_channel_videos(channel_streams, sort_by, page)
    
    return render_template("/legacy/7_4_LegacyChannelStreams.html",
                           videos=paginated_videos,
                           channel=channel_id[1:],
                           channel_info=channel_info,
                           sort_by=sort_by,
                           page=page,
                           total_pages=total_pages)

@app.route("/legacy/<channel_id>/playlists")
def legacy_channel_playlists_page(channel_id):
    channel_info = load_channel_info(channel_id)
    channel_playlists = load_channel_content(channel_id, "Playlists")
    return render_template("/legacy/7_5_LegacyChannelPlaylists.html", 
                            channel_info=channel_info, 
                            channel_playlists=channel_playlists)
    
@app.route("/legacy/<channel_id>/playlist/<playlist_id>")
def legacy_channel_playlist_page(channel_id, playlist_id):
    channel_info = load_channel_info(channel_id)
    channel_playlists = load_channel_content(channel_id, "Playlists")

    playlist = next((pl for pl in channel_playlists if pl["playlist_id"] == playlist_id), None)
    if not playlist:
        return "Playlist not found", 404

    # Pagination settings
    page = int(request.args.get("page", 1))
    videos_per_page = 15
    start_idx = (page - 1) * videos_per_page
    end_idx = start_idx + videos_per_page
    total_videos = len(playlist["videos"])
    paginated_videos = playlist["videos"][start_idx:end_idx]  
    total_pages = (total_videos + videos_per_page - 1) // videos_per_page

    return render_template("/legacy/7_6_LegacyChannelPlaylist.html",
                           channel_info=channel_info,
                           playlist=playlist,
                           paginated_videos=paginated_videos,
                           page=page,
                           total_pages=total_pages)

@app.route("/legacy/<channel_id>/about")
def legacy_channel_about_page(channel_id):
    channels = load_channels()
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        abort(404)
    channel_info = load_channel_info(channel_id)
    return render_template("/legacy/7_7_LegacyChannelAbout.html",
                           channel_info=channel_info)

@app.route("/legacy/<channel_id>/<video_id>")
def legacy_video_page(channel_id, video_id):
    if "user" in session:
        username = session["user"]
        history_path = f"data/history/{username}_history.json"

        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []
            
        channel_videos = load_channel_content(channel_id, "Videos") or []
        channel_shorts = load_channel_content(channel_id, "Shorts") or []
        channel_streams = load_channel_content(channel_id, "Streams") or []
        all_vids = channel_videos + channel_shorts + channel_streams
        if not all_vids:
            abort(404)
        video = next((v for v in all_vids if v["video_id"] == video_id), None)
        if not video:
            abort(404)

        history = [entry for entry in history if entry["video_id"] != video_id]
        history.insert(0, {
            "title": video["title"],
            "duration": video["duration"],
            "uploader_id": channel_id,
            "video_id": video_id,
            "watched_at": get_formatted_datetime()
        })

        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)

    videos = load_all_videos()
    random_videos = random.sample(videos, min(18, len(videos)))
    channel_info = load_channel_info(channel_id)
    return render_template("/legacy/6_LegacyVideos.html",
                           video=video,
                           videos=random_videos,
                           channel_info=channel_info)

@app.route("/legacy/search")
def legacy_search():
    query = request.args.get('q', '').lower()
    if not query:
        abort(404)

    query = query.strip().lower()
    videos = load_all_videos()
    matched_videos = [video for video in videos if query in video['title'].lower()]

    page = int(request.args.get("page", 1))
    videos_per_page = 15
    start_idx = (page - 1) * videos_per_page
    end_idx = start_idx + videos_per_page
    paginated_videos = matched_videos[start_idx:end_idx]
    total_pages = (len(matched_videos) + videos_per_page - 1) // videos_per_page

    return render_template("/legacy/4_LegacySearch.html",
                           query=query,
                           videos=paginated_videos,
                           page=page,
                           total_pages=total_pages,
                           total_Channels=len(load_channels()))


@app.route("/legacy/settings", methods=["GET", "POST"])
def legacy_settings():
    if "user" not in session:
        return redirect(url_for("login"))
    if get_current_user_access() == "modern":
        return redirect(url_for("modern_settings"))
        
    username = session["user"]
    users = load_users()
    user_info = users.get(username, {})
    user_history = load_user_history(username)
    recent_history = user_history[:3]
    settings = load_settings()
    
    if request.method == "POST":
        new_access = request.form.get("access_type")
        new_theme = request.form.get("legacy_theme")
        
        if new_access not in ["legacy", "modern"]:
            return "Invalid access type", 400
        if new_theme not in ["light", "dark"]:
            return "Invalid theme mode", 400

        users[username]["access_type"] = new_access
        users[username]["legacy_theme"] = new_theme

        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
        
        # Refresh the page after POST (redirect pattern)
        return redirect(url_for("legacy_settings"))
    
    current_access = user_info.get("access_type", "legacy")
    current_theme = user_info.get("legacy_theme", "light")
    
    return render_template("/legacy/5_LegacySettings.html",
        current_access=current_access,
        current_theme=current_theme,
        username=username,
        recent_history=recent_history,
        locations=settings["locations"], 
        total_Channels=len(load_channels()),
        total_Videos=len(load_all_videos()),
        settings=settings,
        rights=get_current_user_rights()
    )

@app.route("/legacy/history")
def legacy_history_page():
    if "user" not in session:
        return redirect(url_for("login"))
        
    username = session["user"]
    user_history = load_user_history(username)
    
    page = int(request.args.get("page", 1))
    videos_per_page = 15
    start_idx = (page - 1) * videos_per_page    
    end_idx = start_idx + videos_per_page    
    paginated_videos = user_history[start_idx:end_idx]    
    total_pages = (len(user_history) + videos_per_page - 1) // videos_per_page    
    return render_template("/legacy/8_LegacyHistory.html",
                           videos=paginated_videos,
                           page=page,
                           total_pages=total_pages)

@app.route("/legacy/ChannelManagement")
def legacy_Channel_Management_page():
    if "user" not in session:
        return redirect(url_for("login"))
    if get_current_user_rights() != "admin":
        abort(403)
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    settings = load_settings()
    return render_template("/legacy/9_0_LegacyChannelManagement.html", 
                            channels=channels, 
                            locations=settings["locations"], 
                            on_channel_management=True)
                            
@app.route("/legacy/ChannelManagement/<channel_id>")
def legacy_Specific_Channel_Management_page(channel_id):
    if "user" not in session:
        return redirect(url_for("login"))
    if get_current_user_rights() != "admin":
        abort(403)
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    channel_info = load_channel_info(channel_id)
    return render_template("/legacy/9_1_LegacyChannelSpecificManagement.html", 
                            channels=channels, 
                            channel_info=channel_info, 
                            on_channel_management=True)

@app.route("/legacy/AccountManagement")
def legacy_Account_Management_page_list():
    if get_current_user_rights() != "admin":
        abort(403)
    if "user" not in session:
        return redirect(url_for("login"))
    users = load_users()
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    return render_template("/legacy/10_0_LegacyAccountList.html", 
                            channels=channels, 
                            users=users, 
                            rights=get_current_user_rights())

@app.route("/legacy/AccountManagement/<user_id>")
def legacy_Account_Management_page(user_id):
    if get_current_user_rights() != "admin":
        abort(403)
    if "user" not in session:
        return redirect(url_for("login"))
    user_id = user_id
    user = load_user(user_id)
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    return render_template("/legacy/10_1_LegacyAccountManagement.html", 
                            channels=channels, 
                            user=user, 
                            current_role=user["role"], 
                            rights=get_current_user_rights())
    
# ---------------------------
# Modern Browser
# ---------------------------
@app.route("/")
def modern_home():
    print(session)
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_home"))
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    videos = load_all_videos()
    random_videos = random.sample(videos, min(26, len(videos)))
    return render_template("/modern/2_Home.html",
                            channels=channels,
                            videos=random_videos, 
                            rights=get_current_user_rights())

@app.route("/channels")
def modern_channels():
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channels"))
    channels = load_channels()
    sort_by = request.args.get("sort", "alpha")
    if sort_by == "alpha":
        channels = sorted(channels, key=lambda x: x["uploader"].lower())
    elif sort_by == "most_videos":
        channels = sorted(channels, key=lambda x: int(x["channel_videos"]), reverse=True)
    return render_template("/modern/3_ChannelList.html",
                            channels=channels, 
                            sort_by=sort_by, 
                            rights=get_current_user_rights())

@app.route("/<channel_id>")
def modern_channel_featured_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_home_page", channel_id=channel_id))
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        return '''
            <script>
                alert("Channel not found.");
                window.history.back();
            </script>
        '''
    channel_videos = load_channel_content(channel_id, "Videos") or []
    channel_shorts = load_channel_content(channel_id, "Shorts") or []
    channel_streams = load_channel_content(channel_id, "Streams") or []
    all_vids = channel_videos + channel_shorts + channel_streams
    if not all_vids:
        abort(404)
    all_vids.sort(key=lambda x: datetime.strptime(x["uploaddate"], "%d/%m/%Y"), reverse=True)
    recent_videos = all_vids[0:15]
    channel_info = load_channel_info(channel_id)
    random_channel_videos = random.sample(all_vids, min(15, len(all_vids)))
    return render_template("/modern/7_1_ChannelHome.html",
                           random_videos=random_channel_videos,
                           recent_videos=recent_videos,
                           channel=channel_id[1:],
                           channel_info=channel_info,
                           channels=channels, 
                           rights=get_current_user_rights())

@app.route("/<channel_id>/videos")
def modern_channel_videos_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_videos_page", channel_id=channel_id))
    
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        return '''
            <script>
                alert("Channel not found.");
                window.history.back();
            </script>
        '''
    channel_info = load_channel_info(channel_id)
    return render_template("/modern/7_2_ChannelVideos.html",
                           channels=channels,
                           channel=channel_id,
                           channel_info=channel_info, 
                           rights=get_current_user_rights())

@app.route("/<channel_id>/shorts")
def modern_channel_shorts_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_shorts_page", channel_id=channel_id))
    
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        return '''
            <script>
                alert("Channel not found.");
                window.history.back();
            </script>
        '''
    channel_info = load_channel_info(channel_id)
    return render_template("/modern/7_3_ChannelShorts.html",
                           channels=channels,
                           channel=channel_id,
                           channel_info=channel_info, 
                           rights=get_current_user_rights())

@app.route("/<channel_id>/streams")
def modern_channel_streams_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_streams_page", channel_id=channel_id))
    
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        return '''
            <script>
                alert("Channel not found.");
                window.history.back();
            </script>
        '''
    channel_info = load_channel_info(channel_id)
    return render_template("/modern/7_4_ChannelStreams.html",
                           channels=channels,
                           channel=channel_id,
                           channel_info=channel_info, 
                           rights=get_current_user_rights())

@app.route("/<channel_id>/playlists")
def modern_channel_playlists_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_playlists_page", channel_id=channel_id))
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        return '''
            <script>
                alert("Channel not found.");
                window.history.back();
            </script>
        '''
    channel_playlists = load_channel_content(channel_id, "Playlists")    
    channel_info = load_channel_info(channel_id)
    return render_template("/modern/7_5_ChannelPlaylists.html", 
                            channels=channels,
                            channel_info=channel_info,
                            channel_playlists=channel_playlists, 
                            rights=get_current_user_rights())

@app.route("/<channel_id>/about")
def modern_channel_about_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_about_page", channel_id=channel_id))
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        return '''
            <script>
                alert("Channel not found.");
                window.history.back();
            </script>
        '''
    channel_info = load_channel_info(channel_id)
    return render_template("/modern/7_7_ChannelAbout.html",
                           channel_info=channel_info,
                           channels=channels, 
                           rights=get_current_user_rights())

@app.route("/<channel_id>/<video_id>")
def modern_video_page(channel_id, video_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_video_page", channel_id=channel_id, video_id=video_id))
    if "user" in session:
        username = session["user"]
        history_path = f"data/history/{username}_history.json"

        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []
            
        channel_videos = load_channel_content(channel_id, "Videos") or []
        channel_shorts = load_channel_content(channel_id, "Shorts") or []
        channel_streams = load_channel_content(channel_id, "Streams") or []
        all_vids = channel_videos + channel_shorts + channel_streams
        print(all_vids)
        if not all_vids:
            return '''
                <script>
                    alert("Video not found.");
                    window.history.back();
                </script>
            '''
        video = next((v for v in all_vids if v["video_id"] == video_id), None)
        if not video:
            return '''
                <script>
                    alert("Video not found.");
                    window.history.back();
                </script>
            '''

        history = [entry for entry in history if entry["video_id"] != video_id]
        history.insert(0, {
            "title": video["title"],
            "duration": video["duration"],
            "uploader_id": channel_id,
            "video_id": video_id,
            "watched_at": get_formatted_datetime()
        })

        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)

    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    videos = load_all_videos()
    random_videos = random.sample(videos, min(27, len(videos)))
    channel_info = load_channel_info(channel_id)
    return render_template("/modern/6_Videos.html",
                           video=video,
                           videos=random_videos,
                           channel_info=channel_info,
                           channels=channels, 
                           rights=get_current_user_rights())

@app.route("/<channel_id>/playlist/<playlist_id>")
def modern_channel_playlist_page(channel_id, playlist_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_playlist_page", channel_id=channel_id, video_id=video_id))
    channel_info = load_channel_info(channel_id)
    channel_playlists = load_channel_content(channel_id, "Playlists")

    playlist = load_channel_playlist(channel_id, playlist_id)
    if not playlist:
        return '''
            <script>
                alert("Playlist not found.");
                window.history.back();
            </script>
        '''
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())

    return render_template("/modern/7_6_ChannelPlaylist.html",
                           channel_info=channel_info,
                           playlist=playlist,
                           channels=channels, 
                           rights=get_current_user_rights())
                           
@app.route("/search")
def modern_search():
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_search"))
    query = request.args.get('q', '').lower()
    if not query:
        abort(404)
    query = query.strip().lower()
    return render_template("/modern/4_Search.html", 
                            query=query, 
                            rights=get_current_user_rights())

# Route to render the settings page
@app.route("/settings", methods=["GET"])
def modern_settings():
    if "user" not in session:
        return redirect(url_for("login"))
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_settings"))

    username = session["user"]
    users = load_users()
    user_info = users.get(username, {})
    custom_colour_css = user_info.get("user_theme")
    settings = load_settings()

    return render_template("/modern/5_Settings.html",
        channels=sorted(load_channels(), key=lambda x: x["uploader"].lower()),
        current_access=user_info.get("access_type", "legacy"),
        current_theme=user_info.get("modern_theme", "light"),
        username=username,
        total_Channels=len(load_channels()),
        locations=settings["locations"], 
        total_Videos=len(load_all_videos()),
        custom_colour_css=custom_colour_css,
        settings=settings,
        rights=get_current_user_rights())

@app.route("/api/settings/<type>", methods=["POST"])
def update_settings(type):
    if "user" not in session:
        return redirect(url_for("login"))
        
    settings = load_settings()
    users = load_users()
    username = session["user"]
    data = request.json
    
    if type == "save_download_settings":
        resolution = data.get("resolution")
        fps = data.get("fps")
        settings["video_quality"] = {
            "resolution": int(resolution),
            "fps": int(fps)
        }
        with open("data/settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    elif type == "save_location_settings":
        location = data.get("location")
        settings["locations"].append(location)
        with open("data/settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    elif type == "remove_location_setting":
        location = data.get("location")
        settings["locations"].remove(location)
        with open("data/settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    elif type == "update_archive":
        if global_status_string == "Idle":
            update_archive()
    elif type == "apply":
        new_access = data.get("access_type")
        new_theme = data.get("modern_theme")
        users[username]["access_type"] = new_access
        users[username]["modern_theme"] = new_theme
        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
    elif type == "save_theme":
        new_access = data.get("access_type")
        new_theme = data.get("modern_theme")
        users[username]["access_type"] = new_access
        users[username]["modern_theme"] = new_theme
        users[username]["user_theme"] = [
            data.get("base", "#121212"),
            data.get("text", "#ffffff"),
            data.get("light_base", "#1a1a1a"),
            data.get("interactive", "#ff0000"),
            "custom", "custom", "custom",
            data.get("border", "#ff0000"),
            data.get("hover", "#ffffff"),
            data.get("shadow", "0.7"),
            data.get("icon", "#ffffff")
        ]
        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
    elif type == "password":
        submitted_current_password = data.get("current_password")
        current_hash = users[username]["password"]
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        if not bcrypt.checkpw(submitted_current_password.encode("utf-8"), current_hash.encode("utf-8")):
            return jsonify({"success": False, "message": "Incorrect current password"}), 400

        if new_password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match"}), 400

        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
        users[username]["password"] = hashed_password

        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)

        return jsonify({"success": True})
    else:
        abort(404)
    return jsonify({"success": True})

@app.route("/ChannelManagement")
def modern_Channel_Management_page():
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_Channel_Management_page"))
    if get_current_user_rights() != "admin":
        abort(403)
    if "user" not in session:
        return redirect(url_for("login"))
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    settings = load_settings()
    return render_template("/modern/9_0_ChannelManagement.html", 
                            channels=channels, 
                            locations=settings["locations"], 
                            rights=get_current_user_rights(), 
                            on_channel_management=True)
                            
@app.route("/ChannelManagement/<channel_id>")
def modern_Channel_Specific_Management_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_Specific_Channel_Management_page", channel_id=channel_id))
    if get_current_user_rights() != "admin":
        abort(403)
    if "user" not in session:
        return redirect(url_for("login"))
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    channel_info = load_channel_info(channel_id)
    return render_template("/modern/9_1_ChannelSpecificManagement.html", 
                            channels=channels, 
                            channel_info=channel_info, 
                            rights=get_current_user_rights(), 
                            on_channel_management=True)

@app.route("/AccountManagement")
def modern_Account_Management_page_list():
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_Account_Management_page_list"))
    if get_current_user_rights() != "admin":
        abort(403)
    if "user" not in session:
        return redirect(url_for("login"))
    users = load_users()
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    return render_template("/modern/10_0_AccountList.html", 
                            channels=channels, 
                            users=users, 
                            rights=get_current_user_rights())

@app.route("/AccountManagement/<user_id>")
def modern_Account_Management_page(user_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_Account_Management_page", user_id=user_id))
    if get_current_user_rights() != "admin":
        abort(403)
    if "user" not in session:
        return redirect(url_for("login"))
    user = load_user(user_id)
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    return render_template("/modern/10_1_AccountManagement.html", 
                            channels=channels, 
                            user=user, current_role=user["role"], 
                            rights=get_current_user_rights())

@app.route("/AccountManagement/<user_id>/<type>", methods=["POST"])
def save_account(user_id, type):
    if "user" not in session:
        return redirect(url_for("login"))
    if load_user(user_id) == "None":
        abort(404)
    if get_current_user_rights() != "admin":
        abort(403)
    users = load_users()
    data = request.json
    print(data)
    
    if type == "new_account":
        return make_new_account(data)
    
    username = data.get("username")
    if username not in users:
        return jsonify({"success": False, "message": "Invalid user"}), 400

    if type == "role":
        new_role = data.get("new_role")
        if new_role == "admin" or new_role == "user":
            users[username]["role"] = new_role
            with open("data/users.json", "w", encoding="utf-8") as f:
                json.dump(users, f, indent=4)
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Invalid role. How did you manage this? ._."}), 400
    elif type == "password":
        submitted_current_password = data.get("current_password")
        current_hash = users[username]["password"]
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        if not bcrypt.checkpw(submitted_current_password.encode("utf-8"), current_hash.encode("utf-8")):
            return jsonify({"success": False, "message": "Incorrect current password"}), 400

        if new_password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match"}), 400

        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
        users[username]["password"] = hashed_password

        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
        return jsonify({"success": True})
    elif type == "deleteaccount":
        deletepassword = data.get("deletepassword")
        current_hash = users[username]["password"]

        if not bcrypt.checkpw(deletepassword.encode("utf-8"), current_hash.encode("utf-8")):
            return jsonify({"success": False, "message": "Incorrect password"}), 400
        if session.get("user") == username:
            session.clear()
        os.remove(f"data/History/{username}_history.json")
        users.pop(username)
        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Invalid operation"}), 400
    
@app.route("/history")
def modern_history_page():
    if "user" not in session:
        return redirect(url_for("login"))
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_history_page"))
        
    username = session["user"]
    user_history = load_user_history(username)
    if not user_history:
        no_history = True
    else:
        no_history = False
    channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
       
    return render_template("/modern/8_History.html",
                           channels=channels, 
                           no_history=no_history, 
                           rights=get_current_user_rights())

@app.route("/load_more_videos")
def load_more_videos():
    videos = load_all_videos()
    random_videos = random.sample(videos, min(12, len(videos)))
    return jsonify(random_videos)

#The tree of all trees
@app.route("/<api>/<channel_id>/<type>")
def channel_api(api, channel_id, type):
    sort_by = request.args.get("sort", "newest")
    offset = int(request.args.get("offset", 0))
    playlist_id = request.args.get("playlist_id", 0)
    
    if api == "load_more_content":
        if type == "videos":
            all_videos = load_channel_content(channel_id, "Videos")
        elif type == "shorts":
            all_videos = load_channel_content(channel_id, "Shorts")
        elif type == "streams":
            all_videos = load_channel_content(channel_id, "Streams")
        elif type == "playlists":
            return jsonify(load_channel_content(channel_id, "Playlists")[offset:offset + 30])
        elif type == "playlist":
            return jsonify(load_channel_playlist_videos(channel_id, playlist_id)[offset:offset + 30])
        else:
            abort(404)
        
        if not all_videos:
            abort(404)
        
        if sort_by == "newest":
            all_videos.sort(key=lambda v: v["newest_order"])
        elif sort_by == "oldest":
            all_videos.sort(key=lambda v: v["newest_order"], reverse=True)
        elif sort_by == "most_popular":
            all_videos.sort(key=lambda v: v["views"][0], reverse=True)
        elif sort_by == "least_popular":
            all_videos.sort(key=lambda v: v["views"][0])
        else:
            abort(404)
        
        return jsonify(all_videos[offset:offset + 30])
    
    elif api == "check":
        if type == "videos":
            total = load_channel_content(channel_id, "Videos")
        elif type == "shorts":
            total = load_channel_content(channel_id, "Shorts")
        elif type == "streams":
            total = load_channel_content(channel_id, "Streams")
        elif type == "playlists":
            total = load_channel_content(channel_id, "Playlists")
        elif type == "playlist":
            total = load_channel_playlist_videos(channel_id, playlist_id)
        else:
            abort(404)
        
        if not total:
            abort(404)
        
        return jsonify(len(total))
    else:
        abort(404)


@app.route("/load_more_history/<type>")
def load_more_history(type):
    sort_by = request.args.get("sort", "newest")
    offset = int(request.args.get("offset", 0))
    if "user" not in session:
        return redirect(url_for("login"))
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_history_page"))
    
    username = session["user"]
    user_history = load_user_history(username)
        
    if type == "history":
        if sort_by == "newest":
            user_history
        elif sort_by == "oldest":
            user_history.reverse()
        else:
            abort(404)
        return jsonify(user_history[offset:offset + 30])
        
    elif type == "check":
        return jsonify(len(user_history))
    else:
        abort(404)

@app.route("/load_more_searches/<type>")
def load_more_searches(type):
    offset = int(request.args.get("offset", 0))
    query = request.args.get("query", 0)
    if not query:
        abort(404)
    videos = load_all_videos()
    matched_videos = [video for video in videos if query in video['title'].lower()]
    
    if type == "searches":
        return jsonify(matched_videos[offset:offset + 30])
    elif type == "check":
        return jsonify(len(matched_videos))

# ---------------------------
# iOS 6 APP API
# Will be worked on later... Maybe..
# ---------------------------
# @app.route('/legacyapp', methods=['GET'])
# def legacy_api():
    # return jsonify({"success": True})
    
# @app.route('/legacyapp/home', methods=['GET'])
# def legacy_home_api():
    # videos = load_all_videos()
    # random_videos = random.sample(videos, min(18, len(videos)))
    # return jsonify(random_videos)
    
# @app.route('/legacyapp/channels', methods=['GET'])
# def legacy_channels_api():
    # channels = load_channels()
    # channels = sorted(load_channels(), key=lambda x: x["uploader"].lower())
    # return jsonify(channels)

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0" , port="8000")
