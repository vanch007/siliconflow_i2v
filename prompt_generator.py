"""
Functions for refining text into I2V prompts.
"""

import requests
import json
import logging
from config import API_BASE_URL, LLM_MODEL, get_full_prompt_template

logger = logging.getLogger(__name__)

def refine_prompt(image_description, llm_model=None, prompt_template=None, api_key=None):
    """
    Refine the image description into a high-quality I2V prompt.

    Args:
        image_description (str): Description of the image content
        llm_model (str, optional): The LLM model to use. Defaults to the one in config.
        prompt_template (str, optional): Custom system prompt template to use.

    Returns:
        str: Refined prompt for I2V generation
    """
    try:
        # Get API Key
        if not api_key:
            from config import API_KEY
            api_key = API_KEY

        # Prepare the API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Use the provided model or default to the one in config
        model_to_use = llm_model or LLM_MODEL

        # Use custom prompt template if provided, otherwise use the default from config
        if prompt_template:
            system_message = prompt_template
        else:
            system_message = get_full_prompt_template()

        # Prepare the request payload
        payload = {
            "model": model_to_use,
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": f"Here is an image description. Please refine it into a high-quality prompt for image-to-video generation:\n\n{image_description}"
                }
            ],
            "max_tokens": 512,
            "temperature": 0.7
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
        logger.info(f"API response: {result}")

        # Extract the refined prompt
        message = result["choices"][0]["message"]
        refined_prompt = message.get("content", "")

        # 如果content为空，尝试从reasoning_content获取内容
        if not refined_prompt and "reasoning_content" in message:
            refined_prompt = message["reasoning_content"]
            # 从reasoning_content中提取最后一段作为提示词
            paragraphs = refined_prompt.split('\n\n')
            if len(paragraphs) > 1:
                refined_prompt = paragraphs[-1]

        logger.info(f"Successfully refined prompt: {refined_prompt}")
        return refined_prompt

    except Exception as e:
        logger.error(f"Error refining prompt: {e}")
        if 'response' in locals():
            try:
                logger.error(f"Response status code: {response.status_code}")
                logger.error(f"Response content: {response.text}")
            except:
                pass
        return None
