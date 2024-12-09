
import logging
import os
import re

import boto3
import pytube
import requests
import yt_dlp

from ai.open_ai_utils import generate_response, transcribe_audio
from core import settings
from core.constants import Constants

s3_client = boto3.client('s3')
# Set custom headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# Create custom session
session = requests.Session()
session.headers.update(headers)

# Override pytube's default request session
pytube.request.Request.session = session
LOGGING = logging.getLogger(__name__)

class LoadAudioAndVideo:

   def generate_transcriptions_summary(self, url):
        regex_patterns = [
        r"(?<=v=)[^&#]+",      # Pattern for "watch" URLs
        r"(?<=be/)[^&#]+",     # Pattern for "youtu.be" short URLs
        r"(?<=embed/)[^&#]+"   # Pattern for "embed" URLs
        ]
        
        for pattern in regex_patterns:
            match = re.search(pattern, url)
            if match:
                file_id =  match.group(0)
        output_audio_file_mp3 = f"{settings.RESOURCES_AUDIOS}{file_id}.mp3"
        # output_audio_file_mp3 = f"{file_id}.mp3"
        if not os.path.exists(output_audio_file_mp3):
            LOGGING.info(f"Audio file not available for url: {url}")
            # video = pytube.YouTube(url)
            # video_stream = video.streams.filter(only_audio=True).first()
            # video_stream.download(filename=output_audio_file_mp3)
            ydl_opts = {
                'format': 'bestaudio/best',  # Best audio format
                'outtmpl': output_audio_file_mp3,  # Output path
                'quiet': False,  # Show output,
                'cookies': '../youtube_cookies.txt'
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    print("Download completed.")
            except Exception as e:
                print(f"An error occurred: {e}")
            LOGGING.info(f"Audio file downloaded for url: {url}")
        audio_file = open(output_audio_file_mp3, "rb")
        LOGGING.info(f"Audio tranceiption started for url: {url}")
        transcription = transcribe_audio(audio_file)
        # words = transcription.text.split()
        # chunks = [words[i:i + 1500] for i in range(0, len(words), 1500)]
        # summary = ''
        # LOGGING.info(f"youtube Video url:{url} transcriptions splited into: {len(chunks)}")
        # for chunk in chunks:
        #     text_chunks = ' '.join(chunk)
        #     summary_chunk, tokens_uasage = generate_response(Constants.SUMMARY_PROMPT.format(transcription=text_chunks, youtube_url=url))
        #     summary=summary+" "+summary_chunk
        #     # Upload the file to S3
        return transcription.text
   
  
