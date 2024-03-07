
import logging
import os
import re
from AI.open_ai_utils import generate_response
from core.constants import Constants
import pytube

from core import settings

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

        if not os.path.exists(output_audio_file_mp3):
            LOGGING.info(f"Audio file not available for url: {url}")
            video = pytube.YouTube(url)
            video_stream = video.streams.filter(only_audio=True).first()

            video_stream.download(filename=output_audio_file_mp3)
            LOGGING.info(f"Audio file downloaded for url: {url}")
        audio_file = open(output_audio_file_mp3, "rb")
        LOGGING.info(f"Audio tranceiption started for url: {url}")

        transcription = self.transcribe_audio(audio_file)
        words = transcription.text.split()
        chunks = [words[i:i + 1500] for i in range(0, len(words), 1500)]
        summary = ''
        LOGGING.info(f"youtube Video url:{url} transcriptions splited into: {len(chunks)}")
        for chunk in chunks:
            text_chunks = ' '.join(chunk)
            summary_chunk, tokens_uasage = generate_response(Constants.TRANSCTION_PROMPT.format(transcription=text_chunks, youtube_url=url))
            summary=summary+" "+summary_chunk
        return summary