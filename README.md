# NDBTube
This GitHub repository contains the code for a custom python server built to archive Youtube channels.  
I wouldn't recommend exposing this server to the internet. It wasn't built for that. Just use it on your local network.  
If you find any bugs, let me know.  
View previews of the interface [here](https://github.com/Notdbrand/NDBTube/blob/main/Preview.md).

## Features
- Download all or specific sections of a channel
- Modern view and legacy view
- Legacy view supports old browsers like safari 6
- Channel Management
- And other basic features 

## NDBTube Requirements
- **Python 3**
- Libraries: Flask, bcrypt, yt-dlp
  ```bash
  pip install flask bcrypt yt-dlp
  ```

## NDBTube Setup
### Step 1: Download the Server
Download the server files and place them in your desired directory.

### Step 2: Start the Server
To start the server, run the python script "2_NDBTube.py"

### Step 3: Connect to the Server
The server uses port 8000 by default.  
When you connect to the server, you have to go through the first time setup.

### Step 4: Start archiving
To download your first channel go to channel management, enter a channel url, pick the sections to save and start the download.

## Complete feature list:
### Both:
- Homescreen with random saved videos
- Search function
- Video player with likes, views, upload date, description and link to original video from the saved video
- Channel list that can be sorted by date added, most videos or alphabetical order
- Channel Page:
- Channel homepage with latest videos and random videos.
- Separate Channel video pages for normal videos, shorts and streams. All can be sorted by newest and oldest as well as most and least popular.
- Channel About page with stats of channel and channel description.
- Settings Page:
- If user doesn't have admin rights can logout, change theme and access type, and change their password.
- If user has admin rights; pervious features plus can manage all accounts, create new accounts, manage channels, download settings and shutdown the server.
- Manage Accounts Page:
- Manage account roles, change passwords, and make new accounts
- Manage Channels Page:
- Global status indicator, channel download starter, update channel perferences, check for and download new channel content and delete channels.

### Legacy view:
- The pages with thumbnails only load 15 videos.
- Designed to work well on old browsers.
- Is a static design locked at a width of 768px wide.

### Modern view:
- Has custom theme option in settings were a user can create the own theme.
- This view supports infinite scrolling on pages with thumbnails.
- Has good mobile and desktop support.

## Notes  
### Future Features (Probably):  
- Legacy iOS 5-6 companion app
- External channel storage
- Channel export to ZIP
- Custom colour scheme for legacy
- Might change the name to AUTube
- Proper security measures
- Live video transcoding to support older devices  
- Automatic channel update with PubSubHubbub (Big Maybe)

### Future Updates:
- Fix legacy CSS

### Improvements:
If you have any questions or suggestions, send them to notdebrand@gmail.com or start an issue in this repo.

### Inspiration:
I wanted to host my own instance of tuberepairer but when I found out I had to also host an indivious I couldn't be bothered, so then I decided to make a wrapper for my existing youtube archive and a lot of feature creap later the project is now its own fully fledged archive server. Crazy how things blow up.
