"""
Configuration settings for the SiliconFlow I2V application.
"""

# API Configuration
import os

# 从环境变量获取API Key，如果不存在则使用前端传递的值
# 可以通过以下方式设置 API Key：
# 1. 在 .env 文件中设置 SILICONFLOW_API_KEY=your_api_key_here
# 2. 在系统环境变量中设置 SILICONFLOW_API_KEY
# 3. 在前端界面中输入 API Key
API_KEY = os.environ.get('SILICONFLOW_API_KEY', "")  # 如果环境变量不存在，则默认为空字符串
API_BASE_URL = "https://api.siliconflow.cn/v1"
FREE_API_KEY_URL = "https://cloud.siliconflow.cn/i/TToSB555"

# Model Configuration
VLM_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct"  # Vision Language Model
LLM_MODEL = "Qwen/QwQ-32B"  # Language Model for prompt refinement
I2V_MODEL = "Wan-AI/Wan2.1-I2V-14B-720P"  # Image to Video Model

# Video Configuration
DEFAULT_VIDEO_SIZE = "720x1280"  # Default video resolution
DEFAULT_NEGATIVE_PROMPT = "Vivid tones, overexposed, static, unclear details, subtitles, style, works, paintings, imagery, still, overall grayish, worst quality, low quality, JPEG compression artifacts, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, malformed limbs, fused fingers, motionless imagery, cluttered background, three legs, crowded background, walking backwards"

# Prompt Configuration
# 用户风格提示词 - 显示在界面上供用户修改
DEFAULT_USER_PROMPT = "根据图片帮我生产适合TikTok女士服装的短视频，不要慢动作，也不要大幅度的动作。"

# 系统提示词 - 不显示在界面上，与用户提示词组合使用
SYSTEM_PROMPT = '''
You are an expert at creating high-quality prompts for image-to-video generation models.
Your task is to refine the given image description into a concise, detailed prompt that will
produce a high-quality video that captures the essence of the image.
在编写提示词时，请关注详细、按时间顺序描述动作和场景。包含具体的动作、外貌、镜头角度以及环境细节，
所有内容都应连贯地写在一个段落中，直接从动作开始，描述应具体和精确，将自己想象为在描述镜头脚本的摄影师，
提示词保持在200单词以内。

为了获得最佳效果，请按照以下结构构建提示词：

1. 从主要动作的一句话开始
   示例：A woman with light skin, wearing a blue jacket and a black hat with a veil,
   She first looks down and to her right, then raises her head back up as she speaks.

2. 添加关于动作和手势的具体细节
   示例：She first looks down and to her right, then raises her head back up as she speaks.

3. 精确描述角色/物体的外观
   示例：She has brown hair styled in an updo, light brown eyebrows, and is wearing a white collared shirt under her blue jacket.

4. 包括背景和环境的细节
   示例：The background is out of focus, but shows trees and people in period clothing.

5. 指定镜头角度和移动方式
   示例：The camera remains stationary on her face as she speaks.

6. 描述光线和颜色效果
   示例：The scene is captured in real-life footage, with natural lighting and true-to-life colors.

7. 注意任何变化或突发事件
   示例：A gust of wind blows through the trees, causing the woman's veil to flutter slightly.

Keep the prompt under 200 words and make it specific and descriptive.
Do not include any explanations or notes - just output the refined prompt.
'''

# 完整提示词模板 - 用于后端处理，组合用户提示词和系统提示词
def get_full_prompt_template(user_prompt=None):
    if user_prompt is None:
        user_prompt = DEFAULT_USER_PROMPT
    return f"{user_prompt}\n\n{SYSTEM_PROMPT}"

# File paths
OUTPUT_DIR = "output"  # Directory to save generated videos
