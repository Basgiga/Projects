import requests
import os
import asyncio
from datetime import datetime, timedelta, timezone
from moviepy.editor import VideoFileClip, concatenate_videoclips
from twitchAPI.twitch import Twitch
from moviepy.editor import TextClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import subprocess

"""
tags for my example (later used):

Smash Bros, Smash Bros Ultimate, Daily Dose of smash bros, Daily dose smash, Daily smash,smash bros, smash bros ultimate, daily dose of smash bros,
 smash bro, twitch smash bros, twitch clips smash bros, twitch smash, twitch smash clips, clips, twitch, fighting game, smash bros compliation,
 smash compilation, smash clip compilation

"""

# Twitch API credentials
CLIENT_ID = '-'
CLIENT_SECRET = '-'
ILE_VIDEO = 20
TIME_AMOUNT_DAYS = 1
category_name = 'Super Smash Bros. Ultimate'
#category_name = 'Super Smash Bros. Melee'

# Define the directory for saving downloaded clips
download_directory = 'D:\Pobrane_Opera\ctwitch'

# Create the directory if it doesn't exist
if not os.path.exists(download_directory):
    os.makedirs(download_directory)
    print(f"Created directory: {download_directory}")

def clean_up(modified_clip_filenames, original_clip_filenames):
    # Clean up the individual modified clip files
    for filename in modified_clip_filenames:
        os.remove(filename)
    print("Individual modified clips deleted.")

    # Clean up the original clip files
    for filename in original_clip_filenames:
        os.remove(filename)
    print("Original clips deleted.")


async def add_text_overlay(clip, text, position):
    text_clip = TextClip(text, fontsize=25, color='white', bg_color='transparent').set_position(position).set_duration(clip.duration)
    return CompositeVideoClip([clip, text_clip])

async def get_top_clips(category_name, start_date, end_date, limit):
    clips = []
    names_of_clips = []
    urls = []
    creator = []
    durations = []
    em_urls =[]
    creator_names = []

    # Retrieve information about the specified category
    url = "https://api.twitch.tv/helix/games"

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = f'client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&grant_type=client_credentials'

    try:
        response = requests.post('https://id.twitch.tv/oauth2/token', headers=headers, data=data)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)
    except requests.exceptions.RequestException as err:
        raise SystemExit(err)

    bearer = response.json()['access_token']

    headers = {
        'Authorization': f'Bearer {bearer}',
        'Client-Id': CLIENT_ID,
    }
    params = {
        'name': category_name
    }
    response = requests.get(url, params=params, headers=headers)
    game_info = response.json()
    #print(game_info)
    if not game_info or "data" not in game_info or len(game_info["data"]) == 0:
        print("Category not found.")
        return clips, names_of_clips, urls

    game_id = game_info["data"][0]["id"]

    params = {
        'game_id': game_id,
        'started_at': start_date,
        'ended_at': end_date,
        'first': limit
    }

    url = "https://api.twitch.tv/helix/clips"
    response = requests.get(url, params=params, headers=headers)
    clips_response = response.json()
    #print(clips_response)
    if not clips_response or "data" not in clips_response or len(clips_response["data"]) == 0:
        print("No clips found for the specified category and time range.")
        return clips, names_of_clips, urls

    for clip in clips_response["data"]:
        clip_url = clip["thumbnail_url"]
        clip_title = clip["title"]
        clip_creator = clip["url"]
        duration = clip["duration"]
        em_url = clip["embed_url"]
        c_name = clip["broadcaster_name"]
        clips.append(clip)
        names_of_clips.append(clip_title)
        urls.append(clip_url)
        creator.append(clip_creator)
        durations.append(duration)
        em_urls.append(em_url)
        creator_names.append(c_name)

    return clips, names_of_clips, urls, creator, durations, em_urls, creator_names


# Downloading and merging functions
def download_clip(clip_url, download_path):
    index = clip_url.find('-preview')
    mp4_clip_url = clip_url[:index] + '.mp4'
    r = requests.get(mp4_clip_url)

    if r.headers['Content-Type'] == 'binary/octet-stream':
        if not os.path.exists('files/clips'):
            os.makedirs('files/clips')
        with open(download_path, 'wb') as f:
            f.write(r.content)
            print(f"Clip downloaded and saved at {download_path}")
            return True
    else:
        print(f'Failed to download clip from URL: {mp4_clip_url}')
        return False

async def main():
    try:
        print("Initializing Twitch API client")
        twitch = Twitch(CLIENT_ID, CLIENT_SECRET)
        await twitch.authenticate_app([])

        # Calculate start and end date for yesterday in RFC3339 format
        end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=TIME_AMOUNT_DAYS)
        start_date_str = start_date.isoformat(timespec='seconds')
        end_date_str = end_date.isoformat(timespec='seconds')
        today_date = datetime.now().strftime("%Y-%m-%d")

        # Get the top clips from the specified category
        print(f"Fetching top {ILE_VIDEO} clips for category '{category_name}' from {start_date_str} to {end_date_str}")
        clips, names_of_clips, urls, creators, durations,em_urls, creator_names = await get_top_clips(category_name, start_date_str, end_date_str,
                                                                    limit=ILE_VIDEO)

        if not clips:  # Check if any clips were found
            print("No clips found. Exiting.")
            return

        # Download the clips and add text overlay
        original_clip_flienames = []
        modified_clip_filenames = []
        for i, (clip_url, creator, name_of_clip, names) in enumerate(zip(urls, creators, names_of_clips, creator_names)):
            filename = f'clip_{i}.mp4'
            download_path = os.path.join(download_directory, filename)
            if download_clip(clip_url, download_path):
                original_clip_flienames.append(filename)

                # Add text overlay
                text = f'Creator: twitch.tv/{names}\nClip: {name_of_clip}'
                modified_filename = f'modified_clip_{i}.mp4'
                modified_path = os.path.join(download_directory, modified_filename)
                clip = VideoFileClip(download_path)
                modified_clip = await add_text_overlay(clip, text, position=('left', 'bottom'))
                modified_clip.write_videofile(modified_path, codec='libx264')
                modified_clip_filenames.append(modified_path)
            else:
                print(f"Skipping clip {i + 1} due to download error.")

        # Fuse the modified clips
        if modified_clip_filenames:
            print("Fusing clips")
            clips_to_fuse = [VideoFileClip(filename) for filename in modified_clip_filenames]
            final_clip = concatenate_videoclips(clips_to_fuse, method = 'compose')
            final_clip.write_videofile(f'final_video{today_date}_{category_name}.mp4')

            print("Process completed successfully")
        else:
            print("No valid clips to fuse.")

        # Define the command with arguments
        clip_description = ""
        total_duration_seconds = 0
        for i, (name_of_clip, creator, clip_url, duration, c_name) in enumerate(zip(names_of_clips, creators, em_urls, durations, creator_names), start=1):
            # Calculate total duration in minutes and seconds
            total_minutes = total_duration_seconds // 60
            total_seconds = total_duration_seconds % 60
            formatted_total_duration = f"{total_minutes:02d}:{total_seconds:02d}"

            # Format duration to MM:SS
            duration_minutes = int(duration) // 60
            duration_seconds = int(duration) % 60
            formatted_duration = f"{duration_minutes:02d}:{duration_seconds:02d}"

            # Append clip information to the description
            clip_description += f"[{formatted_total_duration}] #{i} {c_name}: {name_of_clip}\ntwitch.tv/{c_name}\n{creator}\n"

            # Update total duration
            total_duration_seconds += int(duration)

        description = f"""If you enjoyed and wish to see more like the video :) 
        I do not own any of the footage. All rights reserved to their respective authors mentioned in bottom left of the clips. If you enjoyed their content be sure to check their Twitch and YouTube accounts.
        

        {clip_description}
        
        All clips featured in this compilation are owned by their respective creators. My videos adhere to fair use guidelines and offer unique commentary, context, and educational insights. If you have any questions or concerns about the use of your content, please don't hesitate to reach out to me directly, if you wish to be blacklisted or cut your clips from my videos email me with contact below.
        dailydoseofsmashbros@gmail.com
        """
        title = f"{names_of_clips[0]} ({creator_names[0]}) | Daily Dose of {category_name}"
        video = f'final_video{today_date}_{category_name}.mp4'

        print(title,"\n", description, "\n")

        # Write to a text file
        with open(f"video_details_{today_date}_{category_name}.txt", "w") as file:
            file.write(f"{title}\n\n{description}\n")
        command = [
            'py',
            'Youtube_DDOSB.py',
            f'--file={video}',
            f'--title={title}',
            f'--description={description}',
            '--keywords="Smash Bros, Smash Bros Ultimate, Daily Dose of smash bros, Daily dose smash, Daily smash,smash bros, smash bros ultimate, daily dose of smash bros, smash bro, twitch smash bros, twitch clips smash bros, twitch smash, twitch smash clips, clips, twitch, fighting game"',
            '--category=20',
            '--privacyStatus=private'
        ]

        """
        # Run the command
        try:
            subprocess.run(command, check=True)
            print("Command executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
        """

        def add_title_to_thumbnail(thumbnail_url, title, output_path):
            # Download the thumbnail image
            response = requests.get(thumbnail_url)
            thumbnail = Image.open(BytesIO(response.content))

            # Load a font
            font_path = "arial.ttf"  # Ensure this path is correct, you might need to provide a valid path to a .ttf font file on your system
            font_size = 50  # Initial font size
            width, height = thumbnail.size

            def get_font_size_and_lines(font_path, title, max_width, initial_font_size):
                font_size = initial_font_size

                while font_size > 0:
                    font = ImageFont.truetype(font_path, font_size)
                    words = title.split()
                    lines = []
                    current_line = words[0]
                    for word in words[1:]:
                        test_line = current_line + ' ' + word
                        if font.getsize(test_line)[0] <= max_width - 20:
                            current_line = test_line
                        else:
                            lines.append(current_line)
                            current_line = word
                    lines.append(current_line)

                    # Check if the combined height of the lines fits within the image
                    total_height = sum(font.getsize(line)[1] for line in lines)
                    if total_height <= height - 20:
                        return font_size, lines

                    # Reduce the font size if it doesn't fit
                    font_size -= 1

                # If no font size fits, return the smallest possible font size
                return 1, [title]

            # Adjust font size and split text to fit within the image width
            font_size, lines = get_font_size_and_lines(font_path, title, width, font_size)
            font = ImageFont.truetype(font_path, font_size)

            # Create an image object for drawing
            draw = ImageDraw.Draw(thumbnail)

            # Function to draw text with an outline
            def draw_text_with_outline(draw, position, text, font, outline_color, fill_color):
                x, y = position
                # Draw thicker outline
                for i in range(-3, 4):
                    for j in range(-3, 4):
                        if abs(i) + abs(j) >= 3:
                            draw.text((x + i, y + j), text, font=font, fill=outline_color)
                # Draw the fill text
                draw.text(position, text, font=font, fill=fill_color)

            # Calculate text position
            y = (height - (font.getsize(lines[0])[1] * len(lines))) / 2  # Center the text vertically
            for line in lines:
                text_width, text_height = draw.textsize(line, font=font)
                x = 10  # 10 pixels from the left edge
                draw_text_with_outline(draw, (x, y), line, font, outline_color="black", fill_color="white")
                y += text_height

            # Save the modified image
            thumbnail.save(output_path)
            print(f"Thumbnail with text saved at {output_path}")

        # Example usage
        thumbnail_url = urls[0]  # Replace with the URL to your thumbnail image
        title = names_of_clips[0]  # Replace with the title of your video
        output_path = f"DDOSB_{today_date}_{category_name}.jpg"  # The path where you want to save the output image

        add_title_to_thumbnail(thumbnail_url, title, output_path)

        clean_up(modified_clip_filenames,original_clip_flienames)

    except Exception as e:
        print(f"An error occurred: {e}")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
