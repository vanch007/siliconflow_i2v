"""
Main application for SiliconFlow I2V.

This application takes an image as input, processes it with a Vision Language Model,
refines the text into a prompt, and generates a video using the I2V model.
"""

import os
import argparse
import logging
import time
from config import OUTPUT_DIR, DEFAULT_VIDEO_SIZE, DEFAULT_NEGATIVE_PROMPT
from utils import ensure_directory_exists
from image_processor import process_image_with_vlm
from prompt_generator import refine_prompt
from video_generator import generate_video, get_video_status, download_video
from video_extender import extend_video

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_image_to_video(image_path, output_dir=OUTPUT_DIR, negative_prompt=DEFAULT_NEGATIVE_PROMPT, 
                          image_size=DEFAULT_VIDEO_SIZE, seed=None, extend=False):
    """
    Process an image to generate a video.
    
    Args:
        image_path (str): Path to the input image
        output_dir (str): Directory to save the output
        negative_prompt (str): Negative prompt for video generation
        image_size (str): Size of the video
        seed (int): Random seed for generation
        extend (bool): Whether to extend the video
        
    Returns:
        str: Path to the generated video
    """
    try:
        # Ensure the output directory exists
        ensure_directory_exists(output_dir)
        
        # Step 1: Process the image with VLM
        logger.info("Processing image with VLM...")
        image_description = process_image_with_vlm(image_path)
        
        if not image_description:
            logger.error("Failed to process image with VLM")
            return None
        
        logger.info(f"Image description: {image_description[:100]}...")
        
        # Step 2: Refine the prompt
        logger.info("Refining prompt...")
        refined_prompt = refine_prompt(image_description)
        
        if not refined_prompt:
            logger.error("Failed to refine prompt")
            return None
        
        logger.info(f"Refined prompt: {refined_prompt[:100]}...")
        
        # Step 3: Generate the video
        logger.info("Generating video...")
        request_id = generate_video(
            image_path,
            refined_prompt,
            negative_prompt=negative_prompt,
            image_size=image_size,
            seed=seed
        )
        
        if not request_id:
            logger.error("Failed to submit video generation task")
            return None
        
        # Step 4: Wait for the video to be generated
        logger.info("Waiting for video generation to complete...")
        video_info = get_video_status(request_id)
        
        if not video_info:
            logger.error("Failed to get video status")
            return None
        
        # Step 5: Download the video
        video_url = video_info.get("url")
        video_path = download_video(video_url, output_dir)
        
        if not video_path:
            logger.error("Failed to download video")
            return None
        
        logger.info(f"Video generated successfully: {video_path}")
        
        # Step 6: Extend the video if requested
        if extend:
            logger.info("Extending video...")
            extended_video_path = extend_video(
                video_path,
                refined_prompt,
                negative_prompt=negative_prompt,
                image_size=image_size,
                seed=seed
            )
            
            if not extended_video_path:
                logger.error("Failed to extend video")
                return video_path  # Return the original video path
            
            logger.info(f"Video extended successfully: {extended_video_path}")
            return extended_video_path
        
        return video_path
    
    except Exception as e:
        logger.error(f"Error processing image to video: {e}")
        return None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Generate videos from images using SiliconFlow models")
    parser.add_argument("image_path", help="Path to the input image")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Directory to save the output")
    parser.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE_PROMPT, help="Negative prompt for video generation")
    parser.add_argument("--image-size", default=DEFAULT_VIDEO_SIZE, help="Size of the video (e.g., 1280x720)")
    parser.add_argument("--seed", type=int, help="Random seed for generation")
    parser.add_argument("--extend", action="store_true", help="Extend the video using the last frame")
    
    args = parser.parse_args()
    
    # Process the image to generate a video
    video_path = process_image_to_video(
        args.image_path,
        output_dir=args.output_dir,
        negative_prompt=args.negative_prompt,
        image_size=args.image_size,
        seed=args.seed,
        extend=args.extend
    )
    
    if video_path:
        print(f"\nVideo generated successfully: {video_path}")
    else:
        print("\nFailed to generate video")

if __name__ == "__main__":
    main()
