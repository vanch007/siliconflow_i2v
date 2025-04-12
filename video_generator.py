"""
Functions for video generation and retrieval.
"""

import requests
import json
import logging
import os
import base64
from config import API_BASE_URL, I2V_MODEL, DEFAULT_VIDEO_SIZE, DEFAULT_NEGATIVE_PROMPT, OUTPUT_DIR
from utils import download_file, generate_timestamp

logger = logging.getLogger(__name__)

def generate_video(image_path, prompt, model=I2V_MODEL, negative_prompt=DEFAULT_NEGATIVE_PROMPT, image_size=DEFAULT_VIDEO_SIZE, seed=None, api_key=None):
    """
    Generate a video using the I2V model.

    Args:
        image_path (str): Path to the reference image
        prompt (str): Text prompt for video generation
        model (str, optional): Model to use for generation
        negative_prompt (str, optional): Negative prompt
        image_size (str, optional): Size of the video
        seed (int, optional): Random seed for generation

    Returns:
        str: Request ID for the video generation task
    """
    try:
        # Prepare the API request
        if not api_key:
            from config import API_KEY
            api_key = API_KEY

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Encode the image to base64 or use URL
        if image_path.startswith(('http://', 'https://')):
            image = image_path
        else:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
                image = f"data:image/jpeg;base64,{image_data}"

        # 解析图像尺寸
        width, height = image_size.split('x')

        # 尝试新版API
        try:
            # 根据SiliconFlow文档准备请求载荷
            # 参考: https://docs.siliconflow.cn/cn/api-reference/videos/post_videos
            payload = {
                "model": model,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": int(width),
                "height": int(height),
                "image": image
            }

            # Add seed if provided
            if seed is not None:
                payload["seed"] = int(seed)

            # 记录请求载荷以便调试
            logger.info(f"New API request payload: {json.dumps({k: v for k, v in payload.items() if k != 'image'}, ensure_ascii=False)}")

            # Make the API request
            api_url = f"{API_BASE_URL}/videos"
            logger.info(f"Trying new API URL: {api_url}")

            response = requests.post(
                api_url,
                headers=headers,
                json=payload
            )

            # Check if the request was successful
            response.raise_for_status()

            # Parse the response
            result = response.json()

            # 记录完整的响应以便调试
            logger.info(f"New API response: {json.dumps(result, ensure_ascii=False)}")

            # 根据文档提取请求ID
            request_id = result.get("request_id")

        except Exception as e:
            logger.warning(f"New API failed: {e}, trying old API...")

            # 尝试旧版API
            # 准备请求载荷
            payload = {
                "model": model,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "image_size": image_size,  # 旧版API使用image_size而不是分开的width和height
                "image": image
            }

            # Add seed if provided
            if seed is not None:
                payload["seed"] = int(seed)

            # 记录请求载荷以便调试
            logger.info(f"Old API request payload: {json.dumps({k: v for k, v in payload.items() if k != 'image'}, ensure_ascii=False)}")

            # Make the API request
            api_url = f"{API_BASE_URL}/video/submit"
            logger.info(f"Trying old API URL: {api_url}")

            response = requests.post(
                api_url,
                headers=headers,
                json=payload
            )

            # Check if the request was successful
            response.raise_for_status()

            # Parse the response
            result = response.json()

            # 记录完整的响应以便调试
            logger.info(f"Old API response: {json.dumps(result, ensure_ascii=False)}")

            # 旧版API使用requestId而不是request_id
            request_id = result.get("requestId")

        if not request_id:
            logger.error("No request ID returned from API")
            return None

        logger.info(f"Successfully submitted video generation task with request ID: {request_id}")
        return request_id

    except Exception as e:
        logger.error(f"Error generating video: {e}")
        return None

def get_video_status(request_id, api_key=None):
    """
    Check the status of a video generation task and retrieve the video URL when ready.

    Args:
        request_id (str): Request ID for the video generation task

    Returns:
        dict: Video information including URL, or None if not ready or failed
    """
    try:
        # 根据SiliconFlow文档，使用POST请求获取视频状态
        # 参考: https://docs.siliconflow.cn/cn/api-reference/videos/get_videos_status

        # 准备API请求
        if not api_key:
            from config import API_KEY
            api_key = API_KEY

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # 准备请求载荷
        payload = {
            "requestId": request_id
        }

        # 发送API请求
        api_url = f"{API_BASE_URL}/video/status"
        logger.info(f"Checking video status for request_id: {request_id}")

        response = requests.post(
            api_url,
            headers=headers,
            json=payload
        )

        # 检查请求是否成功
        response.raise_for_status()

        # 解析响应
        result = response.json()

        # 记录完整的响应内容（仅在调试级别）
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"API response: {json.dumps(result, ensure_ascii=False)}")

        # 检查状态
        status = result.get("status")

        # 根据状态处理结果
        if status == "Succeed":
            # 视频生成成功，获取URL
            if "results" in result and result["results"] and "videos" in result["results"]:
                videos = result["results"]["videos"]
                if videos and len(videos) > 0 and "url" in videos[0]:
                    video_url = videos[0]["url"]
                    seed = result["results"].get("seed")
                    logger.info(f"Video generation completed successfully for request_id: {request_id}")
                    return {
                        "url": video_url,
                        "seed": seed
                    }

            logger.error(f"Status is Succeed but no video URL found for request_id: {request_id}")
            return None

        elif status in ["Failed", "failed"]:
            # 视频生成失败
            reason = result.get("reason", "Unknown reason")
            logger.error(f"Video generation failed for request_id: {request_id}, reason: {reason}")
            return None

        elif status in ["InQueue", "InProgress"]:
            # 视频仍在生成中
            logger.info(f"Video generation in progress for request_id: {request_id}, status: {status}")
            return None

        else:
            # 未知状态
            logger.warning(f"Unknown status for request_id: {request_id}, status: {status}")
            return None

    except Exception as e:
        logger.error(f"Error checking video status for request_id: {request_id}, error: {e}")
        return None

def download_video(video_url, output_dir=OUTPUT_DIR):
    """
    Download a video from the given URL.

    Args:
        video_url (str): URL of the video
        output_dir (str, optional): Directory to save the video

    Returns:
        str: Path to the downloaded video
    """
    try:
        # Generate a filename with timestamp
        timestamp = generate_timestamp()
        filename = f"video_{timestamp}.mp4"
        output_path = os.path.join(output_dir, filename)

        # Download the video
        return download_file(video_url, output_path)

    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None
