"""RAM-efficient video editing module using FFmpeg streaming."""
import ffmpeg
import asyncio
import aiohttp
import aiofiles
import os
import tempfile
from typing import Optional, Dict, Any, List, Callable, AsyncGenerator
from pathlib import Path
from loguru import logger
from dataclasses import dataclass
from enum import Enum


class EditOperation(Enum):
    """Supported video editing operations."""
    TRIM = "trim"
    CROP = "crop"
    RESIZE = "resize"
    WATERMARK = "watermark"
    COMPRESS = "compress"
    FILTER = "filter"
    MERGE = "merge"
    EXTRACT_AUDIO = "extract_audio"
    ADD_SUBTITLES = "add_subtitles"


@dataclass
class EditConfig:
    """Configuration for video editing operations."""
    operation: EditOperation
    params: Dict[str, Any]
    
    # Trim params
    start_time: Optional[float] = None  # seconds
    end_time: Optional[float] = None  # seconds
    
    # Crop params
    crop_x: Optional[int] = None
    crop_y: Optional[int] = None
    crop_width: Optional[int] = None
    crop_height: Optional[int] = None
    
    # Resize params
    target_width: Optional[int] = None
    target_height: Optional[int] = None
    maintain_aspect_ratio: bool = True
    
    # Watermark params
    watermark_path: Optional[str] = None
    watermark_position: str = "bottom-right"  # top-left, top-right, bottom-left, bottom-right
    watermark_opacity: float = 0.8
    
    # Compress params
    crf: int = 23  # Constant Rate Factor (0-51, lower = better quality)
    preset: str = "medium"  # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    max_bitrate: Optional[str] = None  # e.g., "2M"
    
    # Filter params
    filter_name: Optional[str] = None  # grayscale, blur, sharpen, etc.
    filter_params: Optional[Dict[str, Any]] = None
    
    # Subtitle params
    subtitle_path: Optional[str] = None
    subtitle_style: Optional[str] = None


class StreamDownloader:
    """Memory-efficient video downloader using streaming."""
    
    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
    
    async def download_stream(
        self, 
        url: str, 
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """Download video in chunks to avoid loading entire file into memory."""
        temp_path = f"{output_path}.tmp"
        total_downloaded = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                    resp.raise_for_status()
                    
                    content_length = int(resp.headers.get('content-length', 0))
                    
                    async with aiofiles.open(temp_path, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(self.chunk_size):
                            await f.write(chunk)
                            total_downloaded += len(chunk)
                            
                            if progress_callback and content_length > 0:
                                progress_callback(total_downloaded, content_length)
            
            # Rename temp file to final path
            os.rename(temp_path, output_path)
            logger.info(f"Downloaded {total_downloaded / 1024 / 1024:.2f} MB to {output_path}")
            return output_path
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"Download failed: {e}")
            raise
    
    async def download_to_pipe(self, url: str) -> asyncio.StreamReader:
        """Download video and pipe directly to FFmpeg without saving to disk."""
        read_fd, write_fd = os.pipe()
        
        async def writer():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                        resp.raise_for_status()
                        async with aiofiles.open(write_fd, 'wb', opener=lambda x, y: x) as f:
                            async for chunk in resp.content.iter_chunked(self.chunk_size):
                                await f.write(chunk)
            finally:
                os.close(write_fd)
        
        asyncio.create_task(writer())
        return os.fdopen(read_fd, 'rb')


class VideoEditor:
    """RAM-efficient video editor using FFmpeg streaming pipelines."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.downloader = StreamDownloader()
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def edit_video(
        self,
        input_source: str,  # URL or file path
        output_path: str,
        operations: List[EditConfig],
        keep_intermediate: bool = False
    ) -> str:
        """
        Apply multiple editing operations to a video using streaming.
        
        Args:
            input_source: URL or local file path of input video
            output_path: Destination path for edited video
            operations: List of editing operations to apply
            keep_intermediate: Whether to keep intermediate files
            
        Returns:
            Path to the edited video
        """
        is_url = input_source.startswith(('http://', 'https://'))
        
        if is_url:
            # Download to temp file first (streaming download)
            temp_input = os.path.join(self.temp_dir, f"input_{os.urandom(4).hex()}.mp4")
            try:
                await self.downloader.download_stream(input_source, temp_input)
                input_path = temp_input
            except Exception as e:
                logger.error(f"Failed to download video: {e}")
                raise
        else:
            input_path = input_source
            temp_input = None
        
        try:
            # Build FFmpeg command chain
            result = await self._apply_operations(
                input_path, 
                output_path, 
                operations
            )
            
            logger.info(f"Video editing complete: {output_path}")
            return output_path
            
        finally:
            # Cleanup temp files
            if temp_input and os.path.exists(temp_input) and not keep_intermediate:
                os.remove(temp_input)
    
    async def _apply_operations(
        self,
        input_path: str,
        output_path: str,
        operations: List[EditConfig]
    ) -> str:
        """Apply a chain of FFmpeg operations efficiently."""
        
        if not operations:
            # No operations, just copy
            ffmpeg.input(input_path).output(output_path, c='copy').run(overwrite_output=True)
            return output_path
        
        # Build filter chain for all operations
        stream = ffmpeg.input(input_path)
        video = stream.video
        audio = stream.audio
        filters = []
        
        for op in operations:
            if op.operation == EditOperation.TRIM:
                # Trim is handled via ss/t options, not filters
                continue
                
            elif op.operation == EditOperation.CROP:
                if all([op.crop_x, op.crop_y, op.crop_width, op.crop_height]):
                    video = video.crop(
                        x=op.crop_x,
                        y=op.crop_y,
                        w=op.crop_width,
                        h=op.crop_height
                    )
            
            elif op.operation == EditOperation.RESIZE:
                if op.target_width and op.target_height:
                    if op.maintain_aspect_ratio:
                        video = video.scale(
                            width=op.target_width,
                            height=op.target_height,
                            force_original_aspect_ratio='decrease'
                        )
                    else:
                        video = video.scale(
                            width=op.target_width,
                            height=op.target_height
                        )
            
            elif op.operation == EditOperation.WATERMARK:
                if op.watermark_path:
                    watermark_input = ffmpeg.input(op.watermark_path)
                    position_map = {
                        'top-left': '(0,0)',
                        'top-right': '(main_w-overlay_w,0)',
                        'bottom-left': '(0,main_h-overlay_h)',
                        'bottom-right': '(main_w-overlay_w,main_h-overlay_h)'
                    }
                    overlay_pos = position_map.get(op.watermark_position, 'bottom-right')
                    
                    # Apply opacity
                    watermark_with_opacity = watermark_input.video.filter(
                        'colorchannelmixer',
                        aa=op.watermark_opacity
                    )
                    
                    video = ffmpeg.overlay(video, watermark_with_opacity, overlay_pos)
            
            elif op.operation == EditOperation.FILTER:
                if op.filter_name:
                    video = self._apply_filter(video, op.filter_name, op.filter_params)
        
        # Build output command
        output_kwargs = {
            'c:v': 'libx264',
            'c:a': 'aac',
            'crf': 23,
            'preset': 'medium'
        }
        
        # Find compress operation for quality settings
        for op in operations:
            if op.operation == EditOperation.COMPRESS:
                output_kwargs['crf'] = op.crf
                output_kwargs['preset'] = op.preset
                if op.max_bitrate:
                    output_kwargs['maxrate'] = op.max_bitrate
                    output_kwargs['bufsize'] = str(int(op.max_bitrate.replace('M', '000000').replace('K', '000')) // 2)
        
        # Handle trim separately (needs to be at the input/output level)
        trim_op = next((op for op in operations if op.operation == EditOperation.TRIM), None)
        
        if trim_op:
            input_kwargs = {}
            output_kwargs_trim = {}
            
            if trim_op.start_time:
                input_kwargs['ss'] = trim_op.start_time
            if trim_op.end_time:
                output_kwargs_trim['t'] = trim_op.end_time - trim_op.start_time if trim_op.start_time else trim_op.end_time
            
            # Re-create input with trim parameters
            stream = ffmpeg.input(input_path, **input_kwargs)
            
            # Apply filters to trimmed video
            video = stream.video
            audio = stream.audio
            
            # Re-apply non-trim operations
            for op in operations:
                if op.operation == EditOperation.TRIM:
                    continue
                elif op.operation == EditOperation.CROP:
                    if all([op.crop_x, op.crop_y, op.crop_width, op.crop_height]):
                        video = video.crop(x=op.crop_x, y=op.crop_y, w=op.crop_width, h=op.crop_height)
                elif op.operation == EditOperation.RESIZE:
                    if op.target_width and op.target_height:
                        if op.maintain_aspect_ratio:
                            video = video.scale(width=op.target_width, height=op.target_height,
                                              force_original_aspect_ratio='decrease')
                        else:
                            video = video.scale(width=op.target_width, height=op.target_height)
                elif op.operation == EditOperation.WATERMARK:
                    if op.watermark_path:
                        watermark_input = ffmpeg.input(op.watermark_path)
                        position_map = {
                            'top-left': '(0,0)',
                            'top-right': '(main_w-overlay_w,0)',
                            'bottom-left': '(0,main_h-overlay_h)',
                            'bottom-right': '(main_w-overlay_w,main_h-overlay_h)'
                        }
                        overlay_pos = position_map.get(op.watermark_position, 'bottom-right')
                        watermark_with_opacity = watermark_input.video.filter(
                            'colorchannelmixer', aa=op.watermark_opacity
                        )
                        video = ffmpeg.overlay(video, watermark_with_opacity, overlay_pos)
                elif op.operation == EditOperation.FILTER:
                    if op.filter_name:
                        video = self._apply_filter(video, op.filter_name, op.filter_params)
            
            # Output with trim duration
            if output_kwargs_trim:
                output_kwargs.update(output_kwargs_trim)
        
        # Merge video and audio streams
        output_stream = ffmpeg.output(video, audio, output_path, **output_kwargs)
        
        # Run FFmpeg
        output_stream.run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        return output_path
    
    def _apply_filter(self, video_stream, filter_name: str, params: Optional[Dict] = None):
        """Apply a specific video filter."""
        params = params or {}
        
        if filter_name == 'grayscale':
            return video_stream.hue(s=0)
        elif filter_name == 'blur':
            strength = params.get('strength', 5)
            return video_stream.boxblur(strength)
        elif filter_name == 'sharpen':
            strength = params.get('strength', 0.5)
            return video_stream.unsharp(strength)
        elif filter_name == 'brightness':
            value = params.get('value', 0)
            return video_stream.hue(b=value)
        elif filter_name == 'contrast':
            value = params.get('value', 1)
            return video_stream.hue(c=value)
        elif filter_name == 'flip':
            direction = params.get('direction', 'horizontal')
            if direction == 'vertical':
                return video_stream.vflip()
            else:
                return video_stream.hflip()
        elif filter_name == 'rotate':
            angle = params.get('angle', 90)
            return video_stream.rotate(angle)
        else:
            logger.warning(f"Unknown filter: {filter_name}")
            return video_stream
    
    async def extract_frames(
        self,
        input_source: str,
        output_dir: str,
        frame_interval: float = 1.0,
        max_frames: Optional[int] = None
    ) -> List[str]:
        """Extract frames from video at specified intervals."""
        os.makedirs(output_dir, exist_ok=True)
        
        is_url = input_source.startswith(('http://', 'https://'))
        
        if is_url:
            temp_input = os.path.join(self.temp_dir, f"frame_extract_{os.urandom(4).hex()}.mp4")
            await self.downloader.download_stream(input_source, temp_input)
            input_path = temp_input
        else:
            input_path = input_source
            temp_input = None
        
        try:
            pattern = os.path.join(output_dir, f"frame_%04d.jpg")
            
            ffmpeg_args = {
                'vf': f'fps=1/{frame_interval}',
                'qscale:v': '2'
            }
            
            if max_frames:
                ffmpeg_args['frames:v'] = max_frames
            
            (
                ffmpeg
                .input(input_path)
                .output(pattern, **ffmpeg_args)
                .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            )
            
            # Get list of extracted frames
            frames = sorted([
                os.path.join(output_dir, f) 
                for f in os.listdir(output_dir) 
                if f.endswith('.jpg')
            ])
            
            logger.info(f"Extracted {len(frames)} frames to {output_dir}")
            return frames
            
        finally:
            if temp_input and os.path.exists(temp_input):
                os.remove(temp_input)
    
    async def get_video_info(self, input_source: str) -> Dict[str, Any]:
        """Get video metadata without loading entire file."""
        is_url = input_source.startswith(('http://', 'https://'))
        
        if is_url:
            # For URLs, we need to probe the stream
            probe = ffmpeg.probe(input_source, timeout=30)
        else:
            probe = ffmpeg.probe(input_source)
        
        video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
        
        return {
            'duration': float(probe['format'].get('duration', 0)),
            'size_bytes': int(probe['format'].get('size', 0)),
            'width': int(video_stream.get('width', 0)),
            'height': int(video_stream.get('height', 0)),
            'fps': eval(video_stream.get('r_frame_rate', '0/1')),
            'codec': video_stream.get('codec_name', 'unknown'),
            'bitrate': int(probe['format'].get('bit_rate', 0)),
            'has_audio': audio_stream is not None,
            'audio_codec': audio_stream.get('codec_name') if audio_stream else None
        }
    
    async def compress_video(
        self,
        input_source: str,
        output_path: str,
        target_size_mb: Optional[float] = None,
        quality: str = 'medium'
    ) -> str:
        """Compress video to reduce file size while maintaining quality."""
        quality_map = {
            'low': {'crf': 28, 'preset': 'faster'},
            'medium': {'crf': 23, 'preset': 'medium'},
            'high': {'crf': 18, 'preset': 'slow'}
        }
        
        config = EditConfig(
            operation=EditOperation.COMPRESS,
            params={},
            crf=quality_map.get(quality, quality_map['medium'])['crf'],
            preset=quality_map.get(quality, quality_map['medium'])['preset']
        )
        
        # If target size is specified, calculate bitrate
        if target_size_mb:
            info = await self.get_video_info(input_source)
            duration = info['duration']
            audio_bitrate = 128 * 1000  # Assume 128kbps audio
            
            # Calculate target video bitrate
            target_bits = target_size_mb * 8 * 1024 * 1024
            total_bitrate = target_bits / duration if duration > 0 else 0
            video_bitrate = max(0, total_bitrate - audio_bitrate)
            
            config.max_bitrate = f"{int(video_bitrate / 1000000)}M"
        
        return await self.edit_video(input_source, output_path, [config])
    
    async def create_thumbnail(
        self,
        input_source: str,
        output_path: str,
        timestamp: float = 0.0,
        size: tuple = (320, 180)
    ) -> str:
        """Generate thumbnail from video at specific timestamp."""
        is_url = input_source.startswith(('http://', 'https://'))
        
        if is_url:
            temp_input = os.path.join(self.temp_dir, f"thumb_{os.urandom(4).hex()}.mp4")
            await self.downloader.download_stream(input_source, temp_input)
            input_path = temp_input
        else:
            input_path = input_source
            temp_input = None
        
        try:
            (
                ffmpeg
                .input(input_path, ss=timestamp)
                .output(output_path, vframes=1, s=f'{size[0]}:{size[1]}', **{'qscale:v': 2})
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            logger.info(f"Created thumbnail: {output_path}")
            return output_path
            
        finally:
            if temp_input and os.path.exists(temp_input):
                os.remove(temp_input)
