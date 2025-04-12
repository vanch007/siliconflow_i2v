"""
Utility functions for the SiliconFlow I2V application.
"""

import os
import base64
import requests
import time
from PIL import Image
import io
import logging
from config import OUTPUT_DIR

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_directory_exists(directory):
    """Ensure that the specified directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def encode_image_to_base64(image_path):
    """Encode an image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def download_file(url, output_path):
    """Download a file from a URL to the specified path."""
    try:
        # 检查URL是否有效
        if not url or not url.startswith('http'):
            logger.error(f"Invalid URL: {url}")
            return None

        # 设置请求超时时间和重试机制
        session = requests.Session()
        retry = requests.packages.urllib3.util.retry.Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        # 使用session进行请求
        response = session.get(url, stream=True, timeout=60)
        response.raise_for_status()

        # 检查响应内容类型
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('video/') and not content_type.startswith('application/octet-stream'):
            logger.warning(f"Unexpected content type: {content_type} for URL: {url}")

        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 下载文件
        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # 过滤掉keep-alive新块
                    file.write(chunk)

        # 检查文件大小
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            logger.error(f"Downloaded file is empty: {output_path}")
            os.remove(output_path)  # 删除空文件
            return None

        logger.info(f"Successfully downloaded file ({file_size} bytes) to: {output_path}")
        return output_path
    except requests.exceptions.Timeout:
        logger.error(f"Timeout downloading file from: {url}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error downloading file: {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error downloading file: {e}")
        return None
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return None

def extract_last_frame(video_path, output_path):
    """Extract the last frame from a video file."""
    try:
        import cv2

        # Open the video file
        video = cv2.VideoCapture(video_path)

        # Get the total number of frames
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

        # Set the position to the last frame
        video.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)

        # Read the last frame
        ret, frame = video.read()

        # Release the video file
        video.release()

        if ret:
            # Save the frame as an image
            cv2.imwrite(output_path, frame)
            logger.info(f"Extracted last frame to: {output_path}")
            return output_path
        else:
            logger.error("Failed to extract last frame from video")
            return None
    except Exception as e:
        logger.error(f"Error extracting last frame: {e}")
        return None

def generate_timestamp():
    """Generate a timestamp string for file naming."""
    return time.strftime("%Y%m%d_%H%M%S")

# Initialize output directory
ensure_directory_exists(OUTPUT_DIR)
