"""
Functions for extending videos.
"""

import os
import logging
from utils import extract_last_frame, generate_timestamp
from video_generator import generate_video, get_video_status, download_video
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)

def extend_video(video_path, prompt, model=None, negative_prompt=None, image_size=None, seed=None, api_key=None):
    """
    Extend a video by using its last frame as a reference for generating a new video.

    Args:
        video_path (str): Path to the video to extend
        prompt (str): Text prompt for video generation
        negative_prompt (str, optional): Negative prompt
        image_size (str, optional): Size of the video
        seed (int, optional): Random seed for generation

    Returns:
        str: Path to the extended video
    """
    try:
        # Extract the last frame from the video
        timestamp = generate_timestamp()
        last_frame_path = os.path.join(OUTPUT_DIR, f"last_frame_{timestamp}.jpg")

        extracted_frame = extract_last_frame(video_path, last_frame_path)

        if not extracted_frame:
            logger.error("Failed to extract last frame from video")
            return None

        # Generate a new video using the last frame as reference
        logger.info("Generating new video from last frame...")
        request_id = generate_video(
            extracted_frame,
            prompt,
            model=model,
            negative_prompt=negative_prompt,
            image_size=image_size,
            seed=seed,
            api_key=api_key
        )

        if not request_id:
            logger.error("Failed to submit video generation task")
            return None

        # Wait for the video to be generated
        video_info = get_video_status(request_id, api_key=api_key)

        if not video_info:
            logger.error("Failed to get video status")
            return None

        # Download the generated video
        video_url = video_info.get("url")
        extended_video_path = download_video(video_url)

        if not extended_video_path:
            logger.error("Failed to download extended video")
            return None

        logger.info(f"Successfully extended video: {extended_video_path}")
        return extended_video_path

    except Exception as e:
        logger.error(f"Error extending video: {e}")
        return None
