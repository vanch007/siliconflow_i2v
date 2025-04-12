"""
Functions for image handling and VLM processing.
"""

import requests
import json
import logging
import base64
from config import API_BASE_URL, VLM_MODEL

logger = logging.getLogger(__name__)

def process_image_with_vlm(image_path, vlm_model=None, api_key=None):
    """
    Process an image with the Vision Language Model to identify its content.

    Args:
        image_path (str): Path to the image file
        vlm_model (str, optional): The VLM model to use. Defaults to the one in config.

    Returns:
        str: Text description of the image content
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

        # Encode the image to base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        # Use the provided model or default to the one in config
        model_to_use = vlm_model or VLM_MODEL

        # Prepare the request payload
        payload = {
            "model": model_to_use,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image in detail. Focus on the main subjects, actions, environment, colors, and mood."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1024
        }

        # Make the API request
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )

        # Check if the request was successful
        response.raise_for_status()

        # Parse the response
        result = response.json()

        # Extract the description
        description = result["choices"][0]["message"]["content"]

        logger.info("Successfully processed image with VLM")
        return description

    except Exception as e:
        logger.error(f"Error processing image with VLM: {e}")
        return None
