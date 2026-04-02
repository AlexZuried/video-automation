import ffmpeg
from loguru import logger
import os

class VideoSanitizer:
    def sanitize(self, input_path: str, output_path: str) -> bool:
        """
        Lightweight sanitization using ffmpeg-python:
        1. Convert to 9:16 aspect ratio (crop center)
        2. Normalize audio
        """
        try:
            logger.info(f"Sanitizing video: {input_path}")
            
            # Example ffmpeg command: crop to 9:16 and normalize audio
            # Note: Actual crop values depend on input resolution
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(
                stream, 
                output_path,
                vf="crop=ih*(9/16):ih", # Crop to 9:16
                acodec="aac",
                ar="44100",
                audio_filter="loudnorm=I=-16:TP=-1.5:LRA=11",
                overwrite_output=True
            )
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            
            logger.info(f"Sanitization complete: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Sanitization failed: {e}")
            return False
