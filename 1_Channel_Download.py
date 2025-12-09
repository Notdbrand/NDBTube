import yt_dlp
import os
import locale
from datetime import datetime
import json
import shutil
import sys

locale.setlocale(locale.LC_TIME, '')

with open("data/settings.json", "r") as file:
    server_settings = json.load(file)

def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def RawAndStyledNumberList(n):
    """
    Creates a list with containing the raw number and a styled version.
    Example: [2100000, "2.10M"]
    """
    if n < 1000:
        return [n, str(n)]
    elif n < 10_000:
        return [n, f"{n/1000:.2f}K"]
    elif n < 1_000_000:
        return [n, f"{int(n/1000)}K"]
    elif n < 1_000_000_000:
        return [n, f"{n/1_000_000:.2f}M"]
    else:
        return [n, f"{n/1_000_000_000:.2f}B"]

def format_upload_date(date_str):
    if date_str:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%d/%m/%Y")
    return "Unknown"
    
def format_duration(seconds):
    """
    Returns a formated duration readout from seconds.
    Example: "12:23:34"
    """
    if seconds is None:
        return "00:00"
    else:
        if seconds < 10:
            return f"00:0{seconds}"
        elif seconds < 60:
            return f"00:{seconds}"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def DetermineSections(info):
    """
    Finds the different sections the channel has.
    Either: Videos, Shorts, or Live
    Example: [videos, shorts, streams]
    """
    channel_sections = []
    if info.get('title') != info.get('channel'):
        #Channel has a single section
        channel_sections.append(info.get("webpage_url").rsplit("/", 1)[-1])
    else:
        #Channel has multiple sections
        for entry in info.get('entries'):
            channel_sections.append(entry.get("webpage_url").rsplit("/", 1)[-1])
    return channel_sections

def metadata_lists(info):
    """
    Puts the metadata for each section of the channel 
    into lists and returns them ready for downloading.
    """
    channelcontentdata = dict()
    
    if info.get('title') != info.get('channel'):
        #Channel has a single section
        list_name = info.get("webpage_url").rsplit("/", 1)[-1]
        channelcontentdata[list_name] = info.get('entries')
        
    else:
        #Channel has multiple sections
        for entry in info.get('entries'):
            list_name = entry.get("webpage_url").rsplit("/", 1)[-1]
            channelcontentdata[list_name] = entry.get("entries")
            
    return channelcontentdata

def MemberFilter(info):
    """
    Filters out member only content based on the setting.
    """
    if server_settings.get("ignore_member_only", 0) == 1 and (
        info.get("is_member_only") or info.get("is_member") or info.get("availability") == "members only"
    ):
        return 'Member-only content skipped'
    return None
    
def GetChannelInfo(channel_url, download_location):
    """
    Gets the channel information and videos to download.
    """
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': True,
        'match_filter': MemberFilter
    }    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        if not info or 'entries' not in info:
            raise ValueError("Failed to retrieve channel information.")
        
        uploader_id = info.get('uploader_id', 'UnknownID')
        channel_icon_url = info.get('thumbnails', [{}])[-1].get('url', '')
        thumbnails = info.get('thumbnails', [])
        channel_sections_list = DetermineSections(info)
        output_folder = os.path.join(f"{download_location}", "channels", uploader_id)
        os.makedirs(output_folder, exist_ok=True)
        
        if channel_icon_url:
            ydl_opts_icon = {'outtmpl': os.path.join(output_folder, 'channel.png')}
            with yt_dlp.YoutubeDL(ydl_opts_icon) as ydl_icon:
                ydl_icon.download([channel_icon_url])
        
        if thumbnails:
            banner_url = thumbnails[0].get('url')
            ydl_opts_icon = {'outtmpl': os.path.join(output_folder, 'banner.png')}
            with yt_dlp.YoutubeDL(ydl_opts_icon) as ydl_banner:
                ydl_banner.download([banner_url])
                
        channel_info = {
            'uploader': info.get('uploader'),
            'uploader_id': uploader_id,
            'subscriber_count': RawAndStyledNumberList(info.get('channel_follower_count', 0)),
            'description': info.get('description', 'No description available.'),
            'channel_sections': channel_sections_list,
            'last_checked': datetime.today().strftime('%x')
        }
        
        channelcontentdata = metadata_lists(info)
        return channel_info, channelcontentdata, uploader_id, channel_sections_list

def download_videos(uploader_id, video_entries, output_folder, type):
    video_folder = os.path.join(output_folder, "videos")
    thumbnail_folder = os.path.join(output_folder, "thumbnails")
    video_metadata_file = os.path.join(output_folder, f"{uploader_id}_{type}.json")
    os.makedirs(video_folder, exist_ok=True)
    os.makedirs(thumbnail_folder, exist_ok=True)

    existing_videos = {}
    if os.path.exists(video_metadata_file):
        with open(video_metadata_file, 'r', encoding='utf-8') as f:
            try:
                existing_videos = {video['video_id']: video for video in json.load(f)}
            except json.JSONDecodeError:
                existing_videos = {}

    for video in video_entries:
        video_url = video['url']
        print(f"Processing: {video_url}")

        ydl_opts = {
            'outtmpl': {'default': f"{video_folder}/%(id)s.mp4"},
            'writethumbnail': True,
            'writeinfojson': False,
            'match_filter': MemberFilter,
            'format': (
                f'bestvideo[ext=mp4][height<={server_settings["video_quality"]["resolution"]}][fps<={server_settings["video_quality"]["fps"]}]+bestaudio[ext=m4a]/'
                f'best[ext=mp4][height<={server_settings["video_quality"]["resolution"]}][fps<={server_settings["video_quality"]["fps"]}]/'
                'bestvideo+bestaudio/best'
            ),
            'postprocessors': [
                {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'},
                {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
            ],
            'retries': 5,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'sleep_interval': 5,
            'max_sleep_interval': 15,
        }
        if server_settings["cookie_value"] != "none":
            ydl_opts["cookiesfrombrowser"] = server_settings["cookie_value"]
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=video['id'] not in existing_videos)
        except Exception as e:
            print(f"Skipping video due to extraction error: {video_url} | {e}")
            continue

        if server_settings.get("ignore_member_only", 0) == 1 and (
            info.get("is_member_only") or info.get("is_member") or info.get("availability") == "members only"
        ):
            print(f"Skipping member-only content: {video_url}")
            continue

        video_id = info.get('id')

        if video_id in existing_videos:
            existing_videos[video_id]['likes'] = RawAndStyledNumberList(info.get('like_count', 0))
            existing_videos[video_id]['views'] = RawAndStyledNumberList(info.get('view_count', 0))
        else:
            thumbnail_path = os.path.join(video_folder, f"{info.get('id')}.jpg")
            new_thumbnail_path = os.path.join(thumbnail_folder, f"{info.get('id')}.jpg")

            if os.path.exists(thumbnail_path):
                shutil.move(thumbnail_path, new_thumbnail_path)

            existing_videos[video_id] = {
                'title': info.get('title'),
                'video_id': video_id,
                'likes': RawAndStyledNumberList(info.get('like_count', 0)),
                'views': RawAndStyledNumberList(info.get('view_count', 0)),
                'uploader': info.get('uploader', 'Unknown'),
                'description': info.get('description', ""),
                'uploader_id': info.get('uploader_id', ''),
                'uploaddate': format_upload_date(info.get('upload_date', "")),
                'duration': format_duration(info.get('duration', 0))
            }

    metadata = list(existing_videos.values())
    metadata.sort(key=lambda x: datetime.strptime(x['uploaddate'], "%d/%m/%Y") if x['uploaddate'] != "Unknown" else datetime.min, reverse=True)

    for index, video in enumerate(metadata, start=1):
        video['newest_order'] = index

    return metadata

def calculate_total_views(video_metadata_file):
    total_views = 0
    
    if os.path.exists(video_metadata_file):
        with open(video_metadata_file, 'r', encoding='utf-8') as f:
            try:
                videos = json.load(f)
                total_views = sum(
                    video['views'][0] if isinstance(video.get('views', 0), list) 
                    else video.get('views', 0) for video in videos
                )
            except json.JSONDecodeError:
                total_views = 0
                
    return total_views

def update_all_videos(video_metadata, download_location):
    all_videos_path = os.path.join("static", "All_Videos.json")
    
    all_videos = {}
    if os.path.exists(all_videos_path):
        with open(all_videos_path, 'r', encoding='utf-8') as f:
            try:
                all_videos = {video['video_id']: video for video in json.load(f)}
            except json.JSONDecodeError:
                all_videos = {}
    
    for video in video_metadata:
        all_videos[video['video_id']] = {
            'title': video['title'],
            'video_id': video['video_id'],
            'views': video['views'],
            'uploaddate': video['uploaddate'],
            'duration': video['duration'],
            'uploader': video['uploader'],
            'uploader_id': video.get('uploader_id', ''),
            'location': download_location
        }
    
    save_json(list(all_videos.values()), all_videos_path)
    
def get_playlists(channel_url, output_folder, uploader_id):
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True,
            'match_filter': MemberFilter,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"{channel_url}/playlists", download=False)
            
            if not info or 'entries' not in info:
                return []
            
            playlists = []
            for playlist in info['entries']:
                playlist_url = playlist.get('url')
                
                if not playlist_url:
                    continue
                
                playlist_info = ydl.extract_info(playlist_url, download=False)
                #print("Playlist Info:")
                #print(json.dumps(playlist_info, indent=2))
                videos = []
                for idx, entry in enumerate(playlist_info.get('entries', [])):
                    duration = entry.get('duration', 0)
                    videos.append({
                        'order': idx + 1,
                        'uploader': entry.get('uploader', 'Unknown'),
                        'uploader_id': entry.get('uploader_id', 'Unknown'),
                        'video_id': entry.get('id', 'Unknown'),
                        'title': entry.get('title', 'Unknown Title'),
                        'duration': format_duration(duration)
                    })
                
                playlists.append({
                    'playlist_id': playlist_info.get('id', 'Unknown'),
                    'title': playlist_info.get('title', 'Unknown Playlist'),
                    'view_count': playlist_info.get('view_count', 'Unknown Playlist'),
                    'description': playlist_info.get('description', ''),
                    'amount': len(videos),
                    'videos': videos
                })
            
            return playlists
    except:
        return []
        
def load_channel_content_json(uploader_id, type):
    channel_path = f"static/channels/{uploader_id}/{uploader_id}_{type}.json"
    with open(channel_path, "r", encoding="utf-8") as f:
        return json.load(f)
        
        
def process_channel(channel_url, include_videos=False, include_shorts=False, include_streams=False, quick_update=False, location=0):
    download_location = server_settings["locations"][location]
    channel_info, channelcontentdata, uploader_id, sections = GetChannelInfo(channel_url, download_location)
    output_folder = os.path.join(f"{download_location}", "channels", uploader_id)
    os.makedirs(output_folder, exist_ok=True)
    video_views = shorts_views = streams_views = 0
    downloaded_sections = []
    
    #Videos
    try:
        if "videos" in sections and include_videos:
            video_entries = channelcontentdata["videos"]
            video_metadata_file = os.path.join(output_folder, f"{uploader_id}_Videos.json")
            existing_metadata = []
            existing_ids = set()
            if os.path.exists(video_metadata_file):
                with open(video_metadata_file, 'r', encoding='utf-8') as f:
                    try:
                        existing_metadata = json.load(f)
                        existing_ids = {video['video_id'] for video in existing_metadata}
                    except json.JSONDecodeError:
                        existing_metadata = []

            if quick_update:
                video_entries = [v for v in video_entries if v['id'] not in existing_ids]

            if video_entries:
                new_video_metadata = download_videos(uploader_id, video_entries, output_folder, "videos")

                if quick_update:
                    combined_dict = {v['video_id']: v for v in existing_metadata}
                    for v in new_video_metadata:
                        combined_dict[v['video_id']] = v
                    combined_metadata = list(combined_dict.values())
                    combined_metadata.sort(
                        key=lambda x: datetime.strptime(x['uploaddate'], "%d/%m/%Y") if x['uploaddate'] != "Unknown" else datetime.min,
                        reverse=True
                    )
                    for index, video in enumerate(combined_metadata, start=1):
                        video['newest_order'] = index

                    save_json(combined_metadata, video_metadata_file)
                else:
                    new_video_metadata.sort(
                        key=lambda x: datetime.strptime(x['uploaddate'], "%d/%m/%Y") if x['uploaddate'] != "Unknown" else datetime.min,
                        reverse=True
                    )
                    for index, video in enumerate(new_video_metadata, start=1):
                        video['newest_order'] = index

                    save_json(new_video_metadata, video_metadata_file)

                update_all_videos(new_video_metadata, download_location)
            else:
                print("No new videos found.")
    except Exception as e:
        print(f"Channel doesn't have any normal videos or an error occurred: {e}")
    
    #Shorts
    try:
        if "shorts" in sections and include_shorts:
            shorts_entries = channelcontentdata["shorts"]
            shorts_metadata_file = os.path.join(output_folder, f"{uploader_id}_Shorts.json")
            existing_metadata = []
            existing_ids = set()
            if os.path.exists(shorts_metadata_file):
                with open(shorts_metadata_file, 'r', encoding='utf-8') as f:
                    try:
                        existing_metadata = json.load(f)
                        existing_ids = {video['video_id'] for video in existing_metadata}
                    except json.JSONDecodeError:
                        existing_metadata = []

            if quick_update:
                shorts_entries = [v for v in shorts_entries if v['id'] not in existing_ids]

            if shorts_entries:
                new_metadata = download_videos(uploader_id, shorts_entries, output_folder, "shorts")

                if quick_update:
                    combined_dict = {v['video_id']: v for v in existing_metadata}
                    for v in new_metadata:
                        combined_dict[v['video_id']] = v
                    combined_metadata = list(combined_dict.values())
                    combined_metadata.sort(
                        key=lambda x: datetime.strptime(x['uploaddate'], "%d/%m/%Y") if x['uploaddate'] != "Unknown" else datetime.min,
                        reverse=True
                    )
                    for index, video in enumerate(combined_metadata, start=1):
                        video['newest_order'] = index

                    save_json(combined_metadata, video_metadata_file)
                else:
                    new_metadata.sort(
                        key=lambda x: datetime.strptime(x['uploaddate'], "%d/%m/%Y") if x['uploaddate'] != "Unknown" else datetime.min,
                        reverse=True
                    )
                    for index, video in enumerate(new_metadata, start=1):
                        video['newest_order'] = index

                    save_json(new_metadata, shorts_metadata_file)

                update_all_videos(new_metadata, download_location)
            else:
                print("No new shorts found.")
    except Exception as e:
        print(f"Channel doesn't have any shorts or an error occurred: {e}")

    #Streams
    try:
        if "streams" in sections and include_streams:
            streams_entries = channelcontentdata["streams"]
            streams_metadata_file = os.path.join(output_folder, f"{uploader_id}_Streams.json")
            existing_metadata = []
            existing_ids = set()
            if os.path.exists(streams_metadata_file):
                with open(streams_metadata_file, 'r', encoding='utf-8') as f:
                    try:
                        existing_metadata = json.load(f)
                        existing_ids = {video['video_id'] for video in existing_metadata}
                    except json.JSONDecodeError:
                        existing_metadata = []

            if quick_update:
                streams_entries = [v for v in streams_entries if v['id'] not in existing_ids]

            if streams_entries:
                new_metadata = download_videos(uploader_id, streams_entries, output_folder, "streams")

                if quick_update:
                    combined_dict = {v['video_id']: v for v in existing_metadata}
                    for v in new_metadata:
                        combined_dict[v['video_id']] = v
                    combined_metadata = list(combined_dict.values())
                    combined_metadata.sort(
                        key=lambda x: datetime.strptime(x['uploaddate'], "%d/%m/%Y") if x['uploaddate'] != "Unknown" else datetime.min,
                        reverse=True
                    )
                    for index, video in enumerate(combined_metadata, start=1):
                        video['newest_order'] = index

                    save_json(combined_metadata, video_metadata_file)
                else:
                    new_metadata.sort(
                        key=lambda x: datetime.strptime(x['uploaddate'], "%d/%m/%Y") if x['uploaddate'] != "Unknown" else datetime.min,
                        reverse=True
                    )
                    for index, video in enumerate(new_metadata, start=1):
                        video['newest_order'] = index

                    save_json(new_metadata, streams_metadata_file)

                update_all_videos(new_metadata, download_location)
            else:
                print("No new streams found.")
    except Exception as e:
        print(f"Channel doesn't have any streams or an error occurred: {e}")
    
    if os.path.isfile(os.path.join(output_folder, f"{uploader_id}_Videos.json")):
        downloaded_sections.append("videos")
        video_views = calculate_total_views(os.path.join(output_folder, f"{uploader_id}_Videos.json"))
        
    if os.path.isfile(os.path.join(output_folder, f"{uploader_id}_Shorts.json")):
        downloaded_sections.append("shorts")
        shorts_views = calculate_total_views(os.path.join(output_folder, f"{uploader_id}_Shorts.json"))
        
    if os.path.isfile(os.path.join(output_folder, f"{uploader_id}_Streams.json")):
        downloaded_sections.append("streams")
        streams_views = calculate_total_views(os.path.join(output_folder, f"{uploader_id}_Streams.json"))
        
    total_views = video_views + shorts_views + streams_views
    videos_folder = os.path.join(output_folder, "videos")
    try: 
        video_count = len([f for f in os.listdir(videos_folder) if os.path.isfile(os.path.join(videos_folder, f))])
    except:
        video_count = 0
    
    #Playlists
    try:
        print("Fetching playlists...")
        playlists = get_playlists(channel_url, output_folder, uploader_id)
        if playlists != []:
            downloaded_sections.append("playlists")
            channel_info["channel_sections"].extend(["playlists"])

        save_json(playlists, os.path.join(output_folder, f"{uploader_id}_Playlists.json"))
    except Exception as e:
        print(f"Channel doesn't have any playlists or an error occurred: {e}")
    
    
    channel_info['total_views'] = RawAndStyledNumberList(total_views)
    channel_info['video_count'] = video_count
    channel_info['downloaded_sections'] = downloaded_sections
    save_json(channel_info, os.path.join(output_folder, "channel.json"))
        
    channels_json_path = os.path.join("static", "channels.json")
    all_channels = []
    
    if os.path.exists(channels_json_path):
        with open(channels_json_path, 'r', encoding='utf-8') as f:
            all_channels = json.load(f)
    
    last_checked_date = datetime.today().strftime('%x')
    channel_found = False
    for channel in all_channels:
        if channel.get('uploader_id') == channel_info.get('uploader_id'):
            channel.update({
                'subscriber_count': channel_info['subscriber_count'],
                'total_views': channel_info['total_views'],
                'channel_videos': str(video_count),
                'channel_URL': f"{channel_url}",
                'downloaded_sections': downloaded_sections,
                'to_download_sections': downloaded_sections,
                'location': download_location,
                'last_checked': last_checked_date
            })
            channel_found = True
            break

    if not channel_found:
        all_channels.append({
            'uploader': channel_info['uploader'],
            'uploader_id': channel_info['uploader_id'],
            'subscriber_count': channel_info['subscriber_count'],
            'total_views': channel_info['total_views'],
            'channel_videos': str(video_count),
            'channel_URL': f"{channel_url}",
            'downloaded_sections': downloaded_sections,
            'to_download_sections': downloaded_sections,
            'location': download_location,
            'last_checked': last_checked_date
        })

    save_json(all_channels, channels_json_path)
    
def main():
    channel_url = input("Enter channel URL: \n")
    include_videos = input("Include Videos? (True/False): \n").strip().lower() == "true"
    include_shorts = input("Include Shorts? (True/False): \n").strip().lower() == "true"
    include_streams = input("Include Streams? (True/False): \n").strip().lower() == "true"
    quick_update = input("Quickly update existing archive of a youtube channel? (True/False): \n").strip().lower() == "true"
    location = int(input("Enter Location option: \n"))
    print(f"[main] Inputs -> Location: {location},  URL: {channel_url}, Videos: {include_videos}, Shorts: {include_shorts}, Streams: {include_streams}, Quick Update: {quick_update}", flush=True)
    process_channel(channel_url, include_videos, include_shorts, include_streams, quick_update, location)

if __name__ == "__main__":
    main()

