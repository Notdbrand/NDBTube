from flask import Flask, render_template, request, abort, jsonify, session, redirect, url_for, send_from_directory
import json
import random
import os
import bcrypt
import secrets
from datetime import datetime
import importlib.util
import threading

global_update_status = {
    'in_progress': False,
    'type': '',
    'progress': '',
    'total': 0,
    'completed': 0,
    'current_channel': '',
    'current_uploader': '' 
}
update_lock = threading.Lock()

spec = importlib.util.spec_from_file_location("channel_download", os.path.join(os.path.dirname(__file__), "1_Channel_Download.py"))
channel_download = importlib.util.module_from_spec(spec)
spec.loader.exec_module(channel_download)

app = Flask(__name__)
app.secret_key = "Set to random for release"
#app.secret_key = secrets.token_hex(16)

#Basic functions
def load_settings():
    with open("data/settings.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_users():
    with open("data/users.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_current_user_access():
    if "user" in session:
        users = load_users()
        user_info = users.get(session["user"], {})
        return user_info.get("access_type", "legacy")
    return "legacy"

def check_login():
    settings = load_settings()
    if settings.get("security") == "login_required" and "user" not in session:
        return redirect(url_for("login"))

@app.before_request
def require_login():
    if request.endpoint not in ["login", "logout", "legacy_app", "legacy_home", "legacy_channels", "static"]:
        login_redirect = check_login()
        if login_redirect:
            return login_redirect

def load_all_videos():
    with open("static/All_Videos.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_channels():
    with open("static/channels.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_channel_videos(channel):
    channel_path = f"static/channels/{channel}/{channel}_Videos.json"
    if not os.path.exists(channel_path):
        return None
    with open(channel_path, "r", encoding="utf-8") as f:
        return json.load(f)
        
def load_channel_shorts(channel):
    channel_path = f"static/channels/{channel}/{channel}_Shorts.json"
    if not os.path.exists(channel_path):
        return None
    with open(channel_path, "r", encoding="utf-8") as f:
        return json.load(f)
        
def load_channel_streams(channel):
    channel_path = f"static/channels/{channel}/{channel}_Streams.json"
    if not os.path.exists(channel_path):
        return None
    with open(channel_path, "r", encoding="utf-8") as f:
        return json.load(f)
        
def load_channel_playlists(channel):
    channel_path = f"static/channels/{channel}/{channel}_Playlists.json"
    if not os.path.exists(channel_path):
        return None
    with open(channel_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_channel_info(channel):
    channel_path = f"static/channels/{channel}/channel.json"
    if not os.path.exists(channel_path):
        return None
    with open(channel_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_user_history(user):
    with open(f"data/history/{user}_history.json", "r", encoding="utf-8") as f:
        return json.load(f)
        
def start_update_job(job_type, total):
    with update_lock:
        if global_update_status['in_progress']:
            raise Exception("Another update is in progress.")
        global_update_status['in_progress'] = True
        global_update_status['type'] = job_type
        global_update_status['total'] = total
        global_update_status['completed'] = 0
        global_update_status['progress'] = "Starting " + job_type

def finish_update_job():
    with update_lock:
        global_update_status['in_progress'] = False
        global_update_status['progress'] = "Finished"
        
def update_channels_job(channels):
    try:
        total = len(channels)
        with update_lock:
            global_update_status['in_progress'] = True
            global_update_status['type'] = 'update_channels'
            global_update_status['total'] = total
            global_update_status['completed'] = 0
            global_update_status['progress'] = "Starting update"
            global_update_status['current_uploader'] = ""
        for i, ch in enumerate(channels):
            with update_lock:
                global_update_status['current_uploader'] = ch['uploader']
            channel_download.process_channel(ch['channel_url'])
            with update_lock:
                global_update_status['completed'] = i + 1
                global_update_status['progress'] = "Updated " + str(i + 1) + " of " + str(total)
        with update_lock:
            global_update_status['in_progress'] = False
            global_update_status['current_uploader'] = ""
        # Optionally, log completion.
    except Exception as e:
        with update_lock:
            global_update_status['progress'] = "Error: " + str(e)
            global_update_status['in_progress'] = False
            global_update_status['current_uploader'] = ""


# ---------------------------
# Both
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        users = load_users()
        username = request.form.get("username")
        password = request.form.get("password")

        user_info = users.get(username)
        if user_info:
            stored_hash = user_info["password"]
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
                session["user"] = username
                return redirect(url_for("modern_home"))

        error = "Invalid credentials"
        return render_template("login.html", error=error)

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

#Mostly a counter for playlists (They are a bit fucky)
@app.route("/static/channels/<channel_id>/thumbnails/<video_id>.jpg")
def serve_thumbnail(channel_id, video_id):
    thumbnail_path = f"static/channels/{channel_id}/thumbnails/{video_id}.jpg"
    if not os.path.exists(thumbnail_path):
        return send_from_directory("data", "404.jpg")
    return send_from_directory(f"static/channels/{channel_id}/thumbnails", f"{video_id}.jpg")

def get_formatted_datetime():
    return datetime.now().strftime("%H:%M %d/%m/%Y")
    
#Theme is locked to account
@app.context_processor
def inject_theme_css():
    theme_css = "Legacy_styles.css"
    if "user" in session:
        users = load_users()
        user_info = users.get(session["user"], {})
        if user_info.get("theme_mode", "light") == "dark":
            theme_css = "Legacy_styles_dark_mode.css"
    return dict(theme_css=theme_css)

#Theme is locked to account
@app.context_processor
def modern_colours_css():
    colour_css = ["#FFFFFF", "#1F1F1F", "#F5F5F5", "#007BFF", "#E9ECEF", "#28A745", "#FFC107", "#CED4DA", "#0056B3", "rgba(0, 0, 0, 0.1)", "False"]
    if "user" in session:
        users = load_users()
        user_info = users.get(session["user"], {})
        if user_info.get("modern_theme", "light") == "dark":
            colour_css = ["#121212", "#E0E0E0", "#1E1E1E", "#007BFF", "#2E2E2E", "#28A745", "#FFC107", "#333333", "#339CFF", "rgba(0, 0, 0, 0.7)", "True"]
        elif user_info.get("modern_theme", "light") == "custom":
            colour_css = user_info.get("user_theme")
    return dict(colour_css=colour_css)

@app.route('/download_channel', methods=['POST'])
def download_channel():
    with update_lock:
        if global_update_status['in_progress']:
            return jsonify(success=False, error="You can only have one download or update operation at a time."), 400
    data = request.get_json()
    channel_url = data.get('channel_url')
    include_shorts = data.get('include_shorts', False)
    include_streams = data.get('include_streams', False)
    if not channel_url:
        return jsonify(success=False, error="No channel URL provided."), 400
    try:
        with update_lock:
            global_update_status['in_progress'] = True
            global_update_status['type'] = 'download'
            global_update_status['total'] = 1
            global_update_status['completed'] = 0
            global_update_status['progress'] = 'Downloading channel (' + channel_url + ')'
            global_update_status['current_channel'] = channel_url
        channel_download.process_channel(channel_url, include_shorts=include_shorts, include_streams=include_streams)
        with update_lock:
            global_update_status['completed'] = 1
            global_update_status['progress'] = 'Download complete'
            global_update_status['in_progress'] = False
            global_update_status['current_channel'] = ''
        return jsonify(success=True)
    except Exception as e:
        with update_lock:
            global_update_status['in_progress'] = False
            global_update_status['current_channel'] = ''
        return jsonify(success=False, error=str(e))


@app.route('/update_selected_channels', methods=['POST'])
def update_selected_channels():
    with update_lock:
        if global_update_status['in_progress']:
            return jsonify(success=False, error="You can only have one download or update operation at a time."), 400
    data = request.get_json()
    channels = data.get('channels')
    if not channels or not isinstance(channels, list):
        return jsonify(success=False, error="No channel data provided."), 400
    thread = threading.Thread(target=update_channels_job, args=(channels,))
    thread.start()
    return jsonify(success=True, message="Update selected started.")

@app.route('/update_all_channels', methods=['POST'])
def update_all_channels():
    with update_lock:
        if global_update_status['in_progress']:
            return jsonify(success=False, error="You can only have one download or update operation at a time."), 400
    channels = load_channels()
    channels_data = [{'channel_url': ch['channel_URL'], 'uploader': ch['uploader']} for ch in channels]
    if len(channels_data) == 0:
        return jsonify(success=False, error="No channels available."), 400
    thread = threading.Thread(target=update_channels_job, args=(channels_data,))
    thread.start()
    return jsonify(success=True, message="Update all started.")

@app.route('/update_status', methods=['GET'])
def update_status():
    with update_lock:
        return jsonify(global_update_status)
        
# ---------------------------
# Legacy Browser
# ---------------------------
@app.route("/legacy/")
def legacy_home():
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
    return render_template("/legacy/3_LegacyChannelList.html", channels=channels, sort_by=sort_by)

@app.route("/legacy/<channel_id>")
def legacy_channel_featured_page(channel_id):
    channels = load_channels()
    if not any(ch["uploader_id"] == channel_id for ch in channels):
        abort(404)
    channel_videos = load_channel_videos(channel_id)
    if not channel_videos:
        abort(404)
    recent_videos = channel_videos[0:3]
    channel_info = load_channel_info(channel_id)
    random_channel_videos = random.sample(channel_videos, min(3, len(channel_videos)))
    return render_template("/legacy/7_1_LegacyChannelFeatured.html",
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
    channel_videos = load_channel_videos(channel_id)
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
    channel_shorts = load_channel_shorts(channel_id)
    channel_info = load_channel_info(channel_id)
    if not channel_shorts:
        abort(404)
    
    sort_by = request.args.get("sort", "newest")
    page = int(request.args.get("page", 1))
    
    paginated_videos, total_pages = process_channel_videos(channel_shorts, sort_by, page)
    
    return render_template("/legacy/7_6_LegacyChannelShorts.html",
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
    channel_streams = load_channel_streams(channel_id)
    channel_info = load_channel_info(channel_id)
    if not channel_streams:
        abort(404)
    
    sort_by = request.args.get("sort", "newest")
    page = int(request.args.get("page", 1))
    
    paginated_videos, total_pages = process_channel_videos(channel_streams, sort_by, page)
    
    return render_template("/legacy/7_2_LegacyChannelVideos.html",
                           videos=paginated_videos,
                           channel=channel_id[1:],
                           channel_info=channel_info,
                           sort_by=sort_by,
                           page=page,
                           total_pages=total_pages)


@app.route("/legacy/<channel_id>/playlists")
def legacy_channel_playlists_page(channel_id):
    channel_info = load_channel_info(channel_id)
    channel_playlists = load_channel_playlists(channel_id)
    return render_template("/legacy/7_3_LegacyChannelPlaylists.html", channel_info=channel_info, channel_playlists=channel_playlists)
    
@app.route("/legacy/<channel_id>/playlist/<playlist_id>")
def legacy_channel_playlist_page(channel_id, playlist_id):
    channel_info = load_channel_info(channel_id)
    channel_playlists = load_channel_playlists(channel_id)

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

    return render_template("/legacy/7_4_LegacyChannelPlaylist.html",
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
    channel_videos = load_channel_videos(channel_id)
    channel_info = load_channel_info(channel_id)
    if not channel_videos:
        abort(404)
    return render_template("/legacy/7_5_LegacyChannelAbout.html",
                           videos=channel_videos,
                           channel=channel_id[1:],
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
            
        channel_videos = load_channel_videos(channel_id) or []
        channel_shorts = load_channel_shorts(channel_id) or []
        channel_streams = load_channel_streams(channel_id) or []
        all_vids = channel_videos + channel_shorts + channel_streams
        if not all_vids:
            abort(404)
        video = next((v for v in all_vids if v["video_id"] == video_id), None)
        if not video:
            abort(404)

        # Remove any previous occurrence of this video
        history = [entry for entry in history if entry["video_id"] != video_id]

        # Insert the new entry at the beginning
        history.insert(0, {
            "title": video["title"],
            "duration": video["duration"],
            "uploader_id": channel_id,
            "video_id": video_id,
            "watched_at": get_formatted_datetime()
        })

        # Save the updated history
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
    videos = load_all_videos()
    matched_videos = [video for video in videos if query in video['title'].lower()]
    return render_template("/legacy/4_LegacySearch.html", query=query, videos=matched_videos)

@app.route("/legacy/settings", methods=["GET", "POST"])
def legacy_settings():
    if "user" not in session:
        return redirect(url_for("login"))
        
    username = session["user"]
    users = load_users()
    user_info = users.get(username, {})
    
    user_history = load_user_history(username)
    recent_history = user_history[0:3]
    
    total_Channels = len(load_channels())
    
    if request.method == "POST":
        new_access = request.form.get("access_type")
        new_theme = request.form.get("theme_mode")
        
        if new_access not in ["legacy", "modern"]:
            return "Invalid access type", 400
        if new_theme not in ["light", "dark"]:
            return "Invalid theme mode", 400

        users[username]["access_type"] = new_access
        users[username]["theme_mode"] = new_theme

        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
            
        accessmessage = "Settings updated."
        current_access = new_access
        current_theme = new_theme
    else:
        accessmessage = None
        current_access = user_info.get("access_type", "legacy")
        current_theme = user_info.get("theme_mode", "light")
        
    return render_template("/legacy/5_LegacySettings.html", accessmessage=accessmessage,
                           current_access=current_access, current_theme=current_theme,
                           username=username, recent_history=recent_history, total_Channels=total_Channels)

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
    channels = load_channels()
    return render_template("/legacy/9_LegacyChannelManagement.html", channels=channels)

    
# ---------------------------
# Modern Browser
# ---------------------------
@app.route("/")
def modern_home():
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_home"))
    channels = load_channels()
    videos = load_all_videos()
    random_videos = random.sample(videos, min(26, len(videos)))
    return render_template("/modern/2_ModernHome.html", channels=channels, videos=random_videos)

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
    return render_template("/modern/5_ModernChannels.html", channels=channels, sort_by=sort_by)

@app.route("/<channel_id>")
def modern_channel_featured_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_featured_page", channel_id=channel_id))
    return render_template("/modern/2_ModernHome.html", channels=load_channels())

@app.route("/<channel_id>/videos")
def modern_channel_videos_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_videos_page", channel_id=channel_id))
    return render_template("/modern/2_ModernHome.html", channels=load_channels())

@app.route("/<channel_id>/playlists")
def modern_channel_playlists_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_playlists_page", channel_id=channel_id))
    return render_template("/modern/2_ModernHome.html", channels=load_channels())
    
@app.route("/<channel_id>/playlist/<playlist_id>")
def modern_channel_playlist_page(channel_id, playlist_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_playlists_page", channel_id=channel_id))
    return render_template("/modern/2_ModernHome.html", channels=load_channels())

@app.route("/<channel_id>/about")
def modern_channel_about_page(channel_id):
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_channel_about_page", channel_id=channel_id))
    return render_template("/modern/2_ModernHome.html", channels=load_channels())

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

        channel_videos = load_channel_videos(channel_id)
        if not channel_videos:
            abort(404)
        video = next((v for v in channel_videos if v["video_id"] == video_id), None)
        if not video:
            abort(404)

        # Remove any previous occurrence of this video
        history = [entry for entry in history if entry["video_id"] != video_id]

        # Insert the new entry at the beginning
        history.insert(0, {
            "title": video["title"],
            "duration": video["duration"],
            "uploader_id": channel_id,
            "video_id": video_id,
            "watched_at": get_formatted_datetime()
        })

        # Save the updated history
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)

    videos = load_all_videos()
    random_videos = random.sample(videos, min(27, len(videos)))
    channel_info = load_channel_info(channel_id)
    return render_template("/modern/4_ModernVideo.html",
                           video=video,
                           videos=random_videos,
                           channel_info=channel_info)

@app.route("/search")
def modern_search():
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_search"))
    query = request.args.get('q', '').lower()
    if not query:
        abort(404)
    videos = load_all_videos()
    matched_videos = [video for video in videos if query in video['title'].lower()]
    return render_template("/modern/6_ModernSearch.html", query=query, videos=matched_videos)

@app.route("/settings", methods=["GET", "POST"])
def modern_settings():
    if "user" not in session:
        return redirect(url_for("login"))
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_settings"))
    
    username = session["user"]
    users = load_users()
    user_info = users.get(username, {})
    
    user_history = load_user_history(username)
    recent_history = user_history[0:3]
    
    total_Channels = len(load_channels())
    
    if request.method == "POST":
        new_access = request.form.get("access_type")
        new_theme = request.form.get("modern_theme")
        
        if new_access not in ["legacy", "modern"]:
            return "Invalid access type", 400
        if new_theme not in ["light", "dark", "custom"]:
            return "Invalid theme mode", 400

        users[username]["access_type"] = new_access
        users[username]["modern_theme"] = new_theme

        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
            
        accessmessage = "Settings updated."
        current_access = new_access
        current_theme = new_theme
    else:
        accessmessage = None
        current_access = user_info.get("access_type", "legacy")
        current_theme = user_info.get("modern_theme", "light")
        
    return render_template("/modern/3_ModernSettings.html", channels=load_channels(), accessmessage=accessmessage,
                           current_access=current_access, current_theme=current_theme,
                           username=username, recent_history=recent_history, total_Channels=total_Channels)

@app.route("/ChannelManagement")
def modern_Channel_Management_page():
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_Channel_Management_page"))
    if "user" not in session:
        return redirect(url_for("login"))
    channels = load_channels()
    return render_template("/modern/9_ModernChannelManagement.html", channels=channels)

@app.route("/history")
def modern_history_page():
    if "user" not in session:
        return redirect(url_for("login"))
    if get_current_user_access() == "legacy":
        return redirect(url_for("legacy_history_page"))
        
    username = session["user"]
    user_history = load_user_history(username)
    
    page = int(request.args.get("page", 1))
    videos_per_page = 27
    start_idx = (page - 1) * videos_per_page    
    end_idx = start_idx + videos_per_page    
    paginated_videos = user_history[start_idx:end_idx]    
    total_pages = (len(user_history) + videos_per_page - 1) // videos_per_page    
    return render_template("/modern/7_ModernHistory.html",
                           videos=paginated_videos,
                           page=page,
                           total_pages=total_pages)

@app.route("/load_more_videos")
def load_more_videos():
    videos = load_all_videos()
    random_videos = random.sample(videos, min(12, len(videos)))
    return jsonify(random_videos)


# ---------------------------
# iOS 6 APP API
# ---------------------------
@app.route('/legacyapp', methods=['GET'])
def legacy_app():
    response = {"success": True}
    return jsonify(response)
    
@app.route('/legacyapp/home', methods=['GET'])
def legacy_home_api():
    videos = load_all_videos()
    random_videos = random.sample(videos, min(18, len(videos)))
    return jsonify(random_videos)
    
@app.route('/legacyapp/channels', methods=['GET'])
def legacy_channels_api():
    channels = load_channels()
    channels = sorted(channels, key=lambda x: x["uploader"].lower())
    return jsonify(channels)

# ---------------------------
# Main Shit
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0" , port="6007")
    #app.run(debug=True)
