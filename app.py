"""
Flask application for SiliconFlow I2V Generator.
"""

import os
import uuid
import json
import sqlite3
import threading
import logging
import time
from datetime import datetime
from pathlib import Path

# 尝试加载.env文件中的环境变量
try:
    from dotenv import load_dotenv
    # 尝试加载.env文件
    env_path = Path('.') / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print("\033[92m成功加载.env文件\033[0m")
    else:
        print("\033[93m未找到.env文件，将使用默认配置\033[0m")
        print("\033[93m可以复制.env.example文件并重命名为.env，然后填入您的API Key\033[0m")
except ImportError:
    print("\033[93m未安装python-dotenv库，无法加载.env文件\033[0m")
    print("\033[93m可以使用 'pip install python-dotenv' 安装\033[0m")

from flask import Flask, render_template, request, jsonify, send_from_directory, url_for, redirect, send_file

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from config import OUTPUT_DIR, DEFAULT_VIDEO_SIZE, DEFAULT_NEGATIVE_PROMPT, I2V_MODEL, VLM_MODEL, LLM_MODEL, DEFAULT_USER_PROMPT, get_full_prompt_template, FREE_API_KEY_URL
from utils import ensure_directory_exists
from image_processor import process_image_with_vlm
from prompt_generator import refine_prompt
from video_generator import generate_video, get_video_status, download_video
from video_extender import extend_video
from video_merger import merge_videos
from database import init_db, get_db, close_db

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = OUTPUT_DIR
app.config['DATABASE'] = 'database.sqlite'

# Ensure directories exist
ensure_directory_exists(app.config['UPLOAD_FOLDER'])
ensure_directory_exists(app.config['OUTPUT_FOLDER'])

# Initialize database
init_db(app)

# 检查ffmpeg是否可用
try:
    import subprocess
    import os

    # 尝试多种方式检测ffmpeg
    ffmpeg_paths = [
        'ffmpeg',  # 默认路径
        '/opt/homebrew/bin/ffmpeg',  # Homebrew安装路径
        '/usr/local/bin/ffmpeg',  # 其他常见路径
        '/usr/bin/ffmpeg'
    ]

    ffmpeg_found = False
    for ffmpeg_path in ffmpeg_paths:
        try:
            result = subprocess.run([ffmpeg_path, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            logger.info(f"ffmpeg找到了，路径: {ffmpeg_path}")
            app.config['FFMPEG_PATH'] = ffmpeg_path
            ffmpeg_found = True
            break
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.debug(f"ffmpeg不在路径: {ffmpeg_path}")
            continue

    if ffmpeg_found:
        app.config['FFMPEG_AVAILABLE'] = True
        logger.info("ffmpeg可用，视频合并功能已启用")
    else:
        # 如果所有路径都失败，则禁用视频合并功能
        app.config['FFMPEG_AVAILABLE'] = False
        logger.warning("ffmpeg不可用，视频合并功能将被禁用。请安装ffmpeg以启用此功能。")
except Exception as e:
    logger.error(f"检查ffmpeg时出错: {str(e)}")
    app.config['FFMPEG_AVAILABLE'] = False
    logger.warning("ffmpeg不可用，视频合并功能将被禁用。请安装ffmpeg以启用此功能。")

# Global task dictionary to track running tasks
# 缓存已处理的图片信息，避免重复处理
# 格式: {image_path: {'description': '...', 'prompt': '...'}}
processed_images = {}

# 正在运行的任务列表
tasks = {}

def process_batch_tasks(task_ids, image_path, params_list):
    """处理批量任务，对同一张图片只进行一次VLM和LLM处理。"""
    try:
        # 更新所有任务状态
        for task_id in task_ids:
            update_task_status(task_id, 'processing_image', '正在处理图片...')

        # 获取每个任务的图片路径
        db = get_db()
        task_image_paths = {}
        for task_id in task_ids:
            task = db.execute('SELECT image_path FROM tasks WHERE id = ?', (task_id,)).fetchone()
            if task and task['image_path']:
                # 构建完整的图片路径
                task_image_paths[task_id] = os.path.join(app.config['UPLOAD_FOLDER'], task['image_path'])
            else:
                # 如果没有找到任务或图片路径，使用默认的图片路径
                task_image_paths[task_id] = image_path

        # 按图片路径分组任务
        tasks_by_image = {}
        for i, task_id in enumerate(task_ids):
            img_path = task_image_paths[task_id]
            if img_path not in tasks_by_image:
                tasks_by_image[img_path] = {
                    'task_ids': [],
                    'params_list': []
                }
            tasks_by_image[img_path]['task_ids'].append(task_id)
            tasks_by_image[img_path]['params_list'].append(params_list[i])

        # 对每个不同的图片进行处理
        for img_path, img_tasks in tasks_by_image.items():
            logger.info(f"处理图片: {img_path}, 任务数: {len(img_tasks['task_ids'])}")

            # 检查是否有预设的提示词
            has_preset_prompt = False
            for params in img_tasks['params_list']:
                if 'prompt' in params and params['prompt']:
                    refined_prompt = params['prompt']
                    has_preset_prompt = True
                    logger.info(f"使用预设的提示词: {refined_prompt}")
                    break

            # 如果没有预设的提示词，则生成新的提示词
            if not has_preset_prompt:
                # 检查图片是否已经处理过
                if img_path in processed_images:
                    # 如果图片已经处理过，直接使用缓存的结果
                    logger.info(f"使用缓存的图片处理结果: {img_path}")
                    image_description = processed_images[img_path]['description']
                    refined_prompt = processed_images[img_path]['prompt']
                else:
                    # 如果图片没有处理过，进行处理
                    # Step 1: 使用VLM处理图片
                    # 使用第一个任务的VLM模型参数
                    vlm_model = img_tasks['params_list'][0].get('vlm_model', VLM_MODEL)
                    api_key = img_tasks['params_list'][0].get('api_key', None)
                    image_description = process_image_with_vlm(img_path, vlm_model=vlm_model, api_key=api_key)

                    if not image_description:
                        for task_id in img_tasks['task_ids']:
                            update_task_status(task_id, 'failed', '处理图片失败')
                        continue

                    # 更新所有任务状态
                    for task_id in img_tasks['task_ids']:
                        update_task_status(task_id, 'refining_prompt', '正在精化提示词...')

                    # Step 2: 精化提示词
                    # 使用第一个任务的LLM模型和提示词模板参数
                    llm_model = img_tasks['params_list'][0].get('llm_model', LLM_MODEL)
                    user_prompt = img_tasks['params_list'][0].get('user_prompt', DEFAULT_USER_PROMPT)
                    # 获取API Key
                    api_key = img_tasks['params_list'][0].get('api_key', None)
                    # 组合用户提示词和系统提示词
                    prompt_template = get_full_prompt_template(user_prompt)
                    refined_prompt = refine_prompt(image_description, llm_model=llm_model, prompt_template=prompt_template, api_key=api_key)

                    if not refined_prompt:
                        for task_id in img_tasks['task_ids']:
                            update_task_status(task_id, 'failed', '精化提示词失败')
                        continue

                    # 将处理结果保存到缓存
                    processed_images[img_path] = {
                        'description': image_description,
                        'prompt': refined_prompt
                    }

            # 更新所有任务的提示词
            for task_id in img_tasks['task_ids']:
                update_task_prompt(task_id, refined_prompt)
                update_task_status(task_id, 'generating_video', '正在生成视频...')

            # 为每个任务生成视频（使用不同的随机种子）
            for i, (task_id, params) in enumerate(zip(img_tasks['task_ids'], img_tasks['params_list'])):
                # 更新任务模型
                model = params.get('model', I2V_MODEL)
                update_task_model(task_id, model)

                # 生成视频
                logger.info(f"为任务 {task_id} 生成视频 (第 {i+1}/{len(img_tasks['task_ids'])} 个)")
                # 获取API Key
                api_key = params.get('api_key', None)

                request_id = generate_video(
                    img_path,
                    refined_prompt,
                    model=model,
                    negative_prompt=params.get('negative_prompt', DEFAULT_NEGATIVE_PROMPT),
                    image_size=params.get('image_size', DEFAULT_VIDEO_SIZE),
                    seed=params.get('seed'),
                    api_key=api_key
                )

                # 更新任务的请求ID
                update_task_request_id(task_id, request_id)

    except Exception as e:
        logger.error(f"处理批量任务时出错: {str(e)}")
        for task_id in task_ids:
            update_task_status(task_id, 'failed', f'错误: {str(e)}')

def process_task(task_id, image_path, params):
    """Background task to process an image and generate a video."""
    try:
        # 获取任务的图片路径
        db = get_db()
        task = db.execute('SELECT image_path FROM tasks WHERE id = ?', (task_id,)).fetchone()
        if task and task['image_path']:
            # 使用数据库中的图片路径
            task_image_path = os.path.join(app.config['UPLOAD_FOLDER'], task['image_path'])
            # 检查文件是否存在
            if not os.path.exists(task_image_path):
                logger.error(f"数据库中的图片路径不存在: {task_image_path}")
                # 如果数据库中的图片路径不存在，使用传入的图片路径
                task_image_path = image_path
        else:
            # 如果没有找到任务或图片路径，使用默认的图片路径
            task_image_path = image_path

        # 再次检查图片是否存在
        if not os.path.exists(task_image_path):
            logger.error(f"图片路径不存在: {task_image_path}")
            update_task_status(task_id, 'failed', '图片文件不存在')
            return

        # 调用批量处理函数，但只处理一个任务
        process_batch_tasks([task_id], task_image_path, [params])

        # 获取请求ID
        db = get_db()
        task = db.execute('SELECT request_id FROM tasks WHERE id = ?', (task_id,)).fetchone()
        request_id = task['request_id'] if task else None

        if not request_id:
            update_task_status(task_id, 'failed', '提交视频生成任务失败')
            return

        # Update task with the request ID
        update_task_request_id(task_id, request_id)

        # Step 4: Wait for the video to be generated
        update_task_status(task_id, 'waiting_for_video', '等待视频生成完成...')

        # 设置最大重试次数和等待时间
        max_retries = 60  # 最多等待60次
        retry_interval = 10  # 每次等待10秒
        retries = 0

        while retries < max_retries:
            # 检查视频状态
            # 获取API Key
            api_key = params.get('api_key', None)
            video_info = get_video_status(request_id, api_key=api_key)

            # 如果获取到视频信息，说明视频已经生成完成
            if video_info:
                break

            # 等待一段时间后再次检查
            time.sleep(retry_interval)
            retries += 1
            logger.info(f"等待视频生成，已重试 {retries}/{max_retries} 次")

        # 如果达到最大重试次数仍未获取到视频信息，则标记为失败
        if not video_info:
            update_task_status(task_id, 'failed', '获取视频状态失败，请稍后再试')
            return

        # Step 5: Download the video
        video_url = video_info.get('url')

        # 设置下载重试参数
        download_retries = 10  # 最多重试下载10次
        download_retry_interval = 5  # 每次重试间隔为5秒
        download_attempt = 0
        downloaded_path = None

        # 重试下载视频
        while download_attempt < download_retries and not downloaded_path:
            # 直接使用download_video函数下载视频
            downloaded_path = download_video(video_url, app.config['OUTPUT_FOLDER'])

            if downloaded_path:
                break

            download_attempt += 1
            logger.info(f"下载视频失败，正在重试 {download_attempt}/{download_retries}")
            update_task_status(task_id, 'downloading_video', f'下载视频中，重试 {download_attempt}/{download_retries}')
            time.sleep(download_retry_interval)

        if not downloaded_path:
            update_task_status(task_id, 'failed', '下载视频失败，请稍后再试')
            return

        # Update task with the video path
        update_task_video_path(task_id, os.path.basename(downloaded_path))

        # Step 6: Extend the video if requested
        if params.get('extend', False):
            update_task_status(task_id, 'extending_video', '正在延长视频...')

            # 获取任务的提示词
            db = get_db()
            task = db.execute('SELECT prompt FROM tasks WHERE id = ?', (task_id,)).fetchone()
            task_prompt = task['prompt'] if task else None

            if not task_prompt:
                update_task_status(task_id, 'completed_with_warning', '视频已生成，但无法获取提示词进行延长')
                return

            extended_video_path = extend_video(
                downloaded_path,
                task_prompt,
                model=params.get('model', I2V_MODEL),
                negative_prompt=params.get('negative_prompt', DEFAULT_NEGATIVE_PROMPT),
                image_size=params.get('image_size', DEFAULT_VIDEO_SIZE),
                seed=params.get('seed'),
                api_key=params.get('api_key')
            )

            if not extended_video_path:
                update_task_status(task_id, 'completed_with_warning', '视频已生成，但延长失败')
                return

            # Update task with the extended video path
            update_task_video_path(task_id, os.path.basename(extended_video_path))

        # Update task status to completed
        update_task_status(task_id, 'completed', '视频生成成功')

    except Exception as e:
        logger.error(f"处理任务 {task_id} 时出错: {str(e)}")
        update_task_status(task_id, 'failed', f'错误: {str(e)}')

def update_task_status(task_id, status, message):
    """Update the status of a task in the database."""
    db = get_db()
    db.execute(
        'UPDATE tasks SET status = ?, message = ?, updated_at = ? WHERE id = ?',
        (status, message, datetime.now().isoformat(), task_id)
    )
    db.commit()

def update_task_prompt(task_id, prompt):
    """Update the prompt of a task in the database."""
    db = get_db()
    db.execute(
        'UPDATE tasks SET prompt = ?, updated_at = ? WHERE id = ?',
        (prompt, datetime.now().isoformat(), task_id)
    )
    db.commit()

def update_task_request_id(task_id, request_id):
    """Update the request ID of a task in the database."""
    db = get_db()
    db.execute(
        'UPDATE tasks SET request_id = ?, updated_at = ? WHERE id = ?',
        (request_id, datetime.now().isoformat(), task_id)
    )
    db.commit()

def update_task_video_path(task_id, video_path):
    """Update the video path of a task in the database."""
    db = get_db()
    db.execute(
        'UPDATE tasks SET video_path = ?, updated_at = ? WHERE id = ?',
        (video_path, datetime.now().isoformat(), task_id)
    )
    db.commit()

def update_task_model(task_id, model):
    """Update the model of a task in the database."""
    db = get_db()
    db.execute(
        'UPDATE tasks SET model = ?, updated_at = ? WHERE id = ?',
        (model, datetime.now().isoformat(), task_id)
    )
    db.commit()

def update_task_request_id(task_id, request_id):
    """Update the request ID of a task in the database."""
    db = get_db()
    db.execute(
        'UPDATE tasks SET request_id = ?, updated_at = ? WHERE id = ?',
        (request_id, datetime.now().isoformat(), task_id)
    )
    db.commit()

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', default_user_prompt=DEFAULT_USER_PROMPT, free_api_key_url=FREE_API_KEY_URL)

@app.route('/tasks')
def task_list():
    """Render the task list page."""
    return render_template('tasks.html')

@app.route('/preview/<task_id>')
def preview(task_id):
    """Render the video preview page."""
    db = get_db()
    task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

    if not task:
        return redirect(url_for('tasks'))

    return render_template('preview.html', task=task)

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks."""
    try:
        db = get_db()
        tasks = db.execute('SELECT * FROM tasks ORDER BY created_at DESC').fetchall()

        # Convert tasks to a list of dictionaries
        task_list = []
        for task in tasks:
            # 获取所有列名
            columns = task.keys()

            # 创建基本任务字典
            task_dict = {
                'id': task['id'],
                'status': task['status'],
                'message': task['message'],
                'created_at': task['created_at'],
                'updated_at': task['updated_at']
            }

            # 添加可能存在的其他字段
            optional_fields = [
                'image_path', 'prompt', 'video_path', 'parent_task_id',
                'request_id', 'model', 'vlm_model', 'llm_model', 'prompt_template'
            ]

            for field in optional_fields:
                if field in columns:
                    task_dict[field] = task[field]
                else:
                    task_dict[field] = None

            task_list.append(task_dict)

        return jsonify(task_list)
    except Exception as e:
        logger.error(f"获取任务列表时出错: {str(e)}")
        return jsonify({'error': f"获取任务列表时出错: {str(e)}"}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task."""
    try:
        db = get_db()
        task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        # 获取所有列名
        columns = task.keys()

        # 创建基本任务字典
        task_dict = {
            'id': task['id'],
            'status': task['status'],
            'message': task['message'],
            'created_at': task['created_at'],
            'updated_at': task['updated_at']
        }

        # 添加可能存在的其他字段
        optional_fields = [
            'image_path', 'prompt', 'video_path', 'parent_task_id',
            'request_id', 'model', 'vlm_model', 'llm_model', 'prompt_template'
        ]

        for field in optional_fields:
            if field in columns:
                task_dict[field] = task[field]
            else:
                task_dict[field] = None

        # 确保模型字段有默认值
        if not task_dict['model']:
            task_dict['model'] = I2V_MODEL

        return jsonify(task_dict)
    except Exception as e:
        logger.error(f"获取任务详情时出错: {str(e)}")
        return jsonify({'error': f"获取任务详情时出错: {str(e)}"}), 500

@app.route('/api/tasks/<task_id>/check_video', methods=['GET'])
def check_task_video(task_id):
    """Check if a video is available for a task and update the task if needed."""
    db = get_db()
    task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

    if not task:
        return jsonify({'error': 'Task not found', 'updated': False}), 404

    # 如果任务已经有视频路径，则不需要检查
    if task['video_path']:
        return jsonify({'message': 'Task already has video', 'updated': False})

    # 如果任务没有request_id，则无法检查视频
    if not task['request_id']:
        return jsonify({'message': 'Task has no request ID', 'updated': False})

    # 检查视频状态
    try:
        # 记录开始检查视频状态
        logger.info(f"Starting video status check for task {task_id} with request_id: {task['request_id']}")

        # 使用新的API检查视频状态
        # 获取API Key
        api_key = request.args.get('api_key', None)
        video_info = get_video_status(task['request_id'], api_key=api_key)

        # 记录视频状态检查结果
        logger.info(f"Video status check for task {task_id}: {video_info}")

        if not video_info:
            # 视频尚未准备好，更新任务状态为等待视频
            if task['status'] != 'waiting_for_video' and task['status'] != 'failed':
                update_task_status(task_id, 'waiting_for_video', '等待视频生成完成')
                logger.info(f"Updated task {task_id} status to 'waiting_for_video'")
            return jsonify({'message': 'Video not ready yet', 'updated': False})

        # 如果有视频URL，下载并更新任务
        video_url = video_info.get('url')
        if video_url:
            # 记录视频URL
            logger.info(f"Video URL for task {task_id}: {video_url}")

            # 下载视频
            downloaded_path = download_video(video_url, app.config['OUTPUT_FOLDER'])

            if downloaded_path:
                # 更新任务状态和视频路径
                update_task_status(task_id, 'completed', '视频生成成功')
                update_task_video_path(task_id, os.path.basename(downloaded_path))

                # 记录下载成功信息
                logger.info(f"Video downloaded for task {task_id}: {downloaded_path}")

                return jsonify({
                    'message': 'Video downloaded and task updated',
                    'updated': True,
                    'video_path': os.path.basename(downloaded_path)
                })
            else:
                # 下载失败
                logger.error(f"Failed to download video for task {task_id}")
                return jsonify({'message': 'Failed to download video', 'updated': False})

        # 视频URL不可用
        return jsonify({'message': 'Video URL not available', 'updated': False})

    except Exception as e:
        logger.error(f"Error checking video status for task {task_id}: {str(e)}")
        return jsonify({'error': str(e), 'updated': False}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task."""
    # Check if the post request has the file part
    if 'image' not in request.files:
        return jsonify({'error': 'No image part'}), 400

    file = request.files['image']

    # If user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Generate a unique filename
    filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Save the file
    file.save(file_path)

    # Get parameters from form
    params = {
        'model': request.form.get('model', I2V_MODEL),
        'vlm_model': request.form.get('vlm_model', VLM_MODEL),
        'llm_model': request.form.get('llm_model', LLM_MODEL),
        'negative_prompt': request.form.get('negative_prompt', DEFAULT_NEGATIVE_PROMPT),
        'image_size': request.form.get('image_size', DEFAULT_VIDEO_SIZE),
        'extend': request.form.get('extend', 'false').lower() == 'true',
        'user_prompt': request.form.get('user_prompt', DEFAULT_USER_PROMPT),
        'api_key': request.form.get('api_key', '')
    }

    # Get seed if provided
    seed = request.form.get('seed')
    if seed and seed.isdigit():
        params['seed'] = int(seed)

    # Generate a task ID
    task_id = str(uuid.uuid4())

    # Create a new task in the database
    db = get_db()
    try:
        # 使用新的表结构，包含所有新字段
        db.execute(
            'INSERT INTO tasks (id, status, message, image_path, model, vlm_model, llm_model, prompt_template, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                task_id, 'pending', '任务已创建', filename,
                params.get('model', I2V_MODEL),
                params.get('vlm_model', VLM_MODEL),
                params.get('llm_model', LLM_MODEL),
                params.get('user_prompt', DEFAULT_USER_PROMPT),
                datetime.now().isoformat(), datetime.now().isoformat()
            )
        )
    except sqlite3.OperationalError:
        # 如果表中没有model字段，使用旧的表结构
        db.execute(
            'INSERT INTO tasks (id, status, message, image_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
            (task_id, 'pending', '任务已创建', filename, datetime.now().isoformat(), datetime.now().isoformat())
        )
    db.commit()

    # 将任务添加到批处理队列
    # 检查是否有批量任务参数
    batch_id = request.form.get('batch_id')

    if batch_id:
        # 如果是批量任务的一部分，将任务添加到批处理列表
        if batch_id not in tasks:
            tasks[batch_id] = {
                'task_ids': [],
                'params_list': []
            }

        tasks[batch_id]['task_ids'].append(task_id)
        tasks[batch_id]['params_list'].append(params)

        # 检查是否是批处理的最后一个任务
        batch_size = int(request.form.get('batch_size', 1))
        batch_index = int(request.form.get('batch_index', 0))

        logger.info(f"添加任务到批处理队列: batch_id={batch_id}, index={batch_index}, size={batch_size}")

        if batch_index == batch_size - 1:
            # 如果是最后一个任务，启动批处理
            batch_data = tasks[batch_id]

            # 启动后台线程处理批量任务
            def run_batch_with_context():
                with app.app_context():
                    # 使用任意图片路径作为默认值，实际上会从数据库中获取每个任务的图片路径
                    process_batch_tasks(
                        batch_data['task_ids'],
                        "",  # 空字符串作为默认图片路径，实际上会从数据库中获取
                        batch_data['params_list']
                    )
                    # 处理完成后清除批处理数据
                    if batch_id in tasks:
                        del tasks[batch_id]

            thread = threading.Thread(target=run_batch_with_context)
            thread.daemon = True
            thread.start()
    else:
        # 如果不是批量任务，直接处理单个任务
        def run_task_with_context():
            with app.app_context():
                process_task(task_id, file_path, params)

        thread = threading.Thread(target=run_task_with_context)
        thread.daemon = True
        thread.start()

    return jsonify({'task_id': task_id})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/output/<filename>')
def output_file(filename):
    """Serve output files."""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task and its associated files."""
    try:
        # 获取任务信息
        db = get_db()
        task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

        if not task:
            return jsonify({'error': '任务不存在'}), 404

        # 删除图片文件（如果存在且没有其他任务使用）
        if task['image_path']:
            # 检查是否有其他任务使用相同的图片
            other_tasks_using_image = db.execute(
                'SELECT COUNT(*) as count FROM tasks WHERE image_path = ? AND id != ?',
                (task['image_path'], task_id)
            ).fetchone()['count']

            if other_tasks_using_image > 0:
                logger.info(f"图片 {task['image_path']} 被其他 {other_tasks_using_image} 个任务使用，不删除")
            else:
                # 如果没有其他任务使用该图片，则删除
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], task['image_path'])
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        logger.info(f"已删除图片文件: {image_path}")
                except Exception as e:
                    logger.error(f"删除图片文件时出错: {str(e)}")

        # 删除视频文件（如果存在且没有其他任务使用）
        if task['video_path']:
            # 检查是否有其他任务使用相同的视频
            other_tasks_using_video = db.execute(
                'SELECT COUNT(*) as count FROM tasks WHERE video_path = ? AND id != ?',
                (task['video_path'], task_id)
            ).fetchone()['count']

            if other_tasks_using_video > 0:
                logger.info(f"视频 {task['video_path']} 被其他 {other_tasks_using_video} 个任务使用，不删除")
            else:
                # 如果没有其他任务使用该视频，则删除
                video_path = os.path.join(app.config['OUTPUT_FOLDER'], task['video_path'])
                try:
                    if os.path.exists(video_path):
                        os.remove(video_path)
                        logger.info(f"已删除视频文件: {video_path}")
                except Exception as e:
                    logger.error(f"删除视频文件时出错: {str(e)}")

        # 从数据库中删除任务
        db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        db.commit()

        return jsonify({'success': True, 'message': '任务已成功删除'})

    except Exception as e:
        logger.error(f"删除任务时出错: {str(e)}")
        return jsonify({'error': f'删除任务时出错: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>/regenerate', methods=['POST'])
def regenerate_task(task_id):
    """Regenerate a task using the same image and prompt."""
    try:
        # 获取API Key
        data = request.json or {}
        api_key = data.get('api_key', None)
        # 获取任务信息
        db = get_db()
        task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

        if not task:
            return jsonify({'error': '任务不存在'}), 404

        # 创建新任务
        new_task_id = str(uuid.uuid4())

        # 获取原始任务的参数
        image_path = task['image_path']
        model = task['model'] if 'model' in task.keys() and task['model'] else I2V_MODEL
        prompt = task['prompt'] if 'prompt' in task.keys() and task['prompt'] else None

        # 创建新任务记录
        db.execute(
            'INSERT INTO tasks (id, status, message, image_path, model, prompt, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (new_task_id, 'pending', '任务已提交，等待处理', image_path, model, prompt, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        db.commit()

        # 准备任务参数
        params = {
            'model': model,
            'negative_prompt': DEFAULT_NEGATIVE_PROMPT,
            'width': 720,
            'height': 1280,
            'api_key': api_key
        }

        # 如果有提示词，添加到参数中
        if prompt:
            params['prompt'] = prompt

        # 启动任务处理线程
        def run_task_with_context():
            with app.app_context():
                # 获取完整的图片路径
                full_image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
                process_task(new_task_id, full_image_path, params)

        thread = threading.Thread(target=run_task_with_context)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': '任务已成功提交再次生成',
            'task_id': new_task_id
        })

    except Exception as e:
        logger.error(f"再次生成任务时出错: {str(e)}")
        return jsonify({'error': f'再次生成任务时出错: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>/last_frame', methods=['GET'])
def get_last_frame(task_id):
    """Get the last frame of a video task."""
    try:
        # 获取任务信息
        db = get_db()
        task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

        if not task:
            return jsonify({'error': '任务不存在'}), 404

        # 检查任务是否有视频
        if not task['video_path']:
            return jsonify({'error': '任务没有生成的视频'}), 400

        # 获取视频路径
        video_path = os.path.join(app.config['OUTPUT_FOLDER'], task['video_path'])
        if not os.path.exists(video_path):
            return jsonify({'error': '视频文件不存在'}), 404

        # 生成最后一帧的缓存文件名
        last_frame_filename = f"last_frame_{task_id}.jpg"
        last_frame_path = os.path.join(app.config['UPLOAD_FOLDER'], last_frame_filename)

        # 如果缓存文件已存在且不是强制刷新，直接返回
        if os.path.exists(last_frame_path) and not request.args.get('refresh'):
            return send_file(last_frame_path, mimetype='image/jpeg')

        # 使用OpenCV提取最后一帧
        import cv2
        logger.info(f"正在使用OpenCV提取视频最后一帧: {video_path}")

        # 打开视频文件
        cap = cv2.VideoCapture(video_path)

        # 检查视频是否成功打开
        if not cap.isOpened():
            logger.error(f"无法打开视频文件: {video_path}")
            # 返回默认的无图片占位图
            return send_file('static/img/no-image.png', mimetype='image/png')

        # 获取视频总帧数
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info(f"视频总帧数: {total_frames}")

        if total_frames <= 0:
            logger.error("视频没有帧")
            # 返回默认的无图片占位图
            return send_file('static/img/no-image.png', mimetype='image/png')

        # 定位到最后一帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)

        # 读取最后一帧
        ret, frame = cap.read()

        # 释放视频资源
        cap.release()

        if not ret:
            logger.error("无法读取视频最后一帧")
            # 返回默认的无图片占位图
            return send_file('static/img/no-image.png', mimetype='image/png')

        # 保存最后一帧为图片
        cv2.imwrite(last_frame_path, frame)
        logger.info(f"成功提取并保存最后一帧: {last_frame_path}")

        if not os.path.exists(last_frame_path):
            # 返回默认的无图片占位图
            return send_file('static/img/no-image.png', mimetype='image/png')

        # 返回图片
        return send_file(last_frame_path, mimetype='image/jpeg')

    except Exception as e:
        logger.error(f"获取视频最后一帧时出错: {str(e)}")
        # 返回默认的无图片占位图
        return send_file('static/img/no-image.png', mimetype='image/png')

@app.route('/api/tasks/<task_id>/regenerate_from_last_frame', methods=['POST'])
def regenerate_from_last_frame(task_id):
    """Regenerate a task using the last frame of the video as the input image."""
    try:
        # 获取API Key和用户提供的提示词
        data = request.json or {}
        api_key = data.get('api_key', None)
        user_prompt = data.get('prompt', None)  # 获取用户提供的提示词

        # 获取任务信息
        db = get_db()
        task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

        if not task:
            return jsonify({'error': '任务不存在'}), 404

        # 检查任务是否有视频
        if not task['video_path']:
            return jsonify({'error': '任务没有生成的视频'}), 400

        # 获取视频路径
        video_path = os.path.join(app.config['OUTPUT_FOLDER'], task['video_path'])
        if not os.path.exists(video_path):
            return jsonify({'error': '视频文件不存在'}), 404

        # 提取视频的最后一帧
        try:
            # 生成唯一的图片文件名
            last_frame_filename = f"last_frame_{uuid.uuid4()}.jpg"
            last_frame_path = os.path.join(app.config['UPLOAD_FOLDER'], last_frame_filename)

            # 使用OpenCV提取最后一帧
            import cv2
            logger.info(f"正在使用OpenCV提取视频最后一帧: {video_path}")

            # 打开视频文件
            cap = cv2.VideoCapture(video_path)

            # 检查视频是否成功打开
            if not cap.isOpened():
                logger.error(f"无法打开视频文件: {video_path}")
                return jsonify({'error': '无法打开视频文件'}), 500

            # 获取视频总帧数
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            logger.info(f"视频总帧数: {total_frames}")

            if total_frames <= 0:
                logger.error("视频没有帧")
                return jsonify({'error': '视频没有帧'}), 500

            # 定位到最后一帧
            cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)

            # 读取最后一帧
            ret, frame = cap.read()

            # 释放视频资源
            cap.release()

            if not ret:
                logger.error("无法读取视频最后一帧")
                return jsonify({'error': '无法读取视频最后一帧'}), 500

            # 保存最后一帧为图片
            cv2.imwrite(last_frame_path, frame)
            logger.info(f"成功提取并保存最后一帧: {last_frame_path}")

            if not os.path.exists(last_frame_path):
                return jsonify({'error': '提取视频最后一帧失败'}), 500

            # 创建新任务
            new_task_id = str(uuid.uuid4())

            # 获取原始任务的参数
            model = task['model'] if 'model' in task.keys() and task['model'] else I2V_MODEL

            # 使用用户提供的提示词，如果没有则使用原始任务的提示词
            prompt = user_prompt if user_prompt else (task['prompt'] if 'prompt' in task.keys() and task['prompt'] else None)

            # 创建新任务记录
            db.execute(
                'INSERT INTO tasks (id, status, message, image_path, model, prompt, parent_task_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (new_task_id, 'pending', '任务已提交，等待处理', last_frame_filename, model, prompt, task_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            db.commit()

            # 准备任务参数
            params = {
                'model': model,
                'negative_prompt': DEFAULT_NEGATIVE_PROMPT,
                'width': 720,
                'height': 1280,
                'api_key': api_key
            }

            # 如果有提示词，添加到参数中
            if prompt:
                params['prompt'] = prompt

            # 启动任务处理线程
            def run_task_with_context():
                with app.app_context():
                    process_task(new_task_id, last_frame_path, params)

            thread = threading.Thread(target=run_task_with_context)
            thread.daemon = True
            thread.start()

            return jsonify({
                'success': True,
                'message': '已成功提取视频最后一帧并提交新任务',
                'task_id': new_task_id
            })

        except Exception as e:
            logger.error(f"提取视频最后一帧时出错: {str(e)}")
            return jsonify({'error': f'提取视频最后一帧时出错: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"使用最后一帧再次生成任务时出错: {str(e)}")
        return jsonify({'error': f'使用最后一帧再次生成任务时出错: {str(e)}'}), 500

@app.route('/api/check_video_status', methods=['POST'])
def check_video_status():
    """Directly check video status with SiliconFlow API."""
    try:
        # 获取请求参数
        data = request.json
        request_id = data.get('request_id')

        if not request_id:
            return jsonify({'error': '缺少request_id参数'}), 400

        # 直接调用SiliconFlow API获取视频状态
        from config import API_BASE_URL
        import requests

        # 获取API Key
        from config import API_KEY
        api_key = request.json.get('api_key', API_KEY)
        if not api_key:
            return jsonify({'error': '缺少API Key'}), 400

        # 准备API请求
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
        logger.info(f"Directly checking video status with API URL: {api_url}")

        response = requests.post(
            api_url,
            headers=headers,
            json=payload
        )

        # 检查请求是否成功
        response.raise_for_status()

        # 解析响应
        result = response.json()

        # 记录完整的响应内容
        logger.info(f"Direct API response: {json.dumps(result, ensure_ascii=False)}")

        return jsonify(result)
    except Exception as e:
        logger.error(f"直接检查视频状态时出错: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/check_all_videos', methods=['GET'])
def check_all_videos():
    """Check all videos that are waiting for completion."""
    try:
        db = get_db()
        # 获取所有处于等待视频状态的任务
        tasks = db.execute(
            'SELECT * FROM tasks WHERE (status = "waiting_for_video" OR status = "generating_video") AND request_id IS NOT NULL AND video_path IS NULL'
        ).fetchall()

        logger.info(f"找到 {len(tasks)} 个等待视频的任务")

        updated_tasks = []

        for task in tasks:
            task_id = task['id']
            request_id = task['request_id']

            logger.info(f"检查任务 {task_id} 的视频状态，request_id: {request_id}")

            # 使用优化后的get_video_status函数获取视频状态
            # 从查询参数中获取API密钥，而不是JSON正文
            api_key = request.args.get('api_key', None)
            video_info = get_video_status(request_id, api_key=api_key)

            # 如果获取到视频信息，则下载并更新任务
            if video_info and 'url' in video_info:
                video_url = video_info['url']
                logger.info(f"获取到视频URL，准备下载: {video_url}")

                if video_url:
                        # 下载视频
                        downloaded_path = download_video(video_url, app.config['OUTPUT_FOLDER'])

                        if downloaded_path:
                            # 更新任务状态和视频路径
                            update_task_status(task_id, 'completed', '视频生成成功')
                            update_task_video_path(task_id, os.path.basename(downloaded_path))

                            updated_tasks.append({
                                'id': task_id,
                                'status': 'completed',
                                'video_path': os.path.basename(downloaded_path)
                            })

                            logger.info(f"任务 {task_id} 的视频已下载并更新")

        return jsonify({
            'success': True,
            'message': f'已检查 {len(tasks)} 个任务，更新 {len(updated_tasks)} 个任务',
            'updated_tasks': updated_tasks
        })
    except Exception as e:
        logger.error(f"检查所有视频时出错: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<string:task_id>/update_video', methods=['POST'])
def update_task_video(task_id):
    """Update task with video URL."""
    try:
        # 确保我们有task_id参数
        if not task_id:
            return jsonify({'error': '缺少task_id参数'}), 400

        data = request.json
        video_url = data.get('video_url')

        if not video_url:
            return jsonify({'error': '缺少video_url参数'}), 400

        # 下载视频
        downloaded_path = download_video(video_url, app.config['OUTPUT_FOLDER'])

        if not downloaded_path:
            return jsonify({'error': '下载视频失败'}), 500

        # 更新任务状态
        update_task_status(task_id, 'completed', '视频生成完成')

        # 更新任务的视频路径
        update_task_video_path(task_id, os.path.basename(downloaded_path))

        return jsonify({
            'success': True,
            'message': '任务视频已更新',
            'video_path': os.path.basename(downloaded_path)
        })
    except Exception as e:
        logger.error(f"更新任务视频时出错: {e}")
        return jsonify({'error': str(e)}), 500

@app.teardown_appcontext
def close_connection(exception):
    """Close the database connection at the end of the request."""
    close_db(exception)

@app.route('/api/test_api_key', methods=['POST'])
def test_api_key():
    """Test if the provided API key is valid."""
    try:
        # 获取API Key
        data = request.json
        api_key = data.get('api_key')

        if not api_key:
            return jsonify({'success': False, 'message': '请提供API Key'}), 400

        # 准备API请求
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # 使用一个简单的API调用来测试API Key是否有效
        # 这里使用模型列表API，这是一个轻量级调用
        import requests
        from config import API_BASE_URL

        response = requests.get(
            f"{API_BASE_URL}/models",
            headers=headers
        )

        # 检查响应状态
        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'API Key 有效'})
        elif response.status_code == 401:
            return jsonify({'success': False, 'message': 'API Key 无效或已过期'})
        else:
            return jsonify({'success': False, 'message': f'API 服务器返回错误: {response.status_code}'})

    except Exception as e:
        logger.error(f"测试API Key时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'测试API Key时出错: {str(e)}'}), 500

@app.route('/api/merge_videos', methods=['POST'])
def merge_videos_api():
    """Merge multiple videos into a single video."""
    try:
        # 获取请求参数
        data = request.json
        task_ids = data.get('task_ids', [])

        # 如果是虚拟的任务ID，返回ffmpeg状态
        if 'test1' in task_ids and 'test2' in task_ids and len(task_ids) == 2:
            if app.config.get('FFMPEG_AVAILABLE', False):
                return jsonify({
                    'success': True,
                    'message': 'ffmpeg可用，视频合并功能已启用',
                    'ffmpeg_path': app.config.get('FFMPEG_PATH', 'ffmpeg')
                })
            else:
                return jsonify({
                    'error': 'ffmpeg不可用，无法合并视频。请安装ffmpeg后再尝试。',
                    'code': 'ffmpeg_not_available'
                })

        # 检查ffmpeg是否可用
        if not app.config.get('FFMPEG_AVAILABLE', False):
            return jsonify({
                'error': 'ffmpeg不可用，无法合并视频。请安装ffmpeg后再尝试。',
                'code': 'ffmpeg_not_available'
            }), 400

        if not task_ids or not isinstance(task_ids, list) or len(task_ids) < 2:
            return jsonify({'error': '至少需要两个有效的任务ID'}), 400

        # 获取API Key
        api_key = data.get('api_key', None)

        # 获取任务信息
        db = get_db()
        video_paths = []
        task_prompts = []
        first_task_image_path = None  # 用于存储第一个任务的图片路径
        first_task_model = None  # 用于存储第一个任务的模型

        for i, task_id in enumerate(task_ids):
            task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

            if not task:
                return jsonify({'error': f'任务 {task_id} 不存在'}), 404

            if not task['video_path']:
                return jsonify({'error': f'任务 {task_id} 没有生成的视频'}), 400

            # 添加完整的视频路径
            video_path = os.path.join(app.config['OUTPUT_FOLDER'], task['video_path'])
            if not os.path.exists(video_path):
                return jsonify({'error': f'视频文件 {task["video_path"]} 不存在'}), 404

            video_paths.append(video_path)

            # 收集提示词用于新任务
            if task['prompt']:
                task_prompts.append(task['prompt'])

            # 保存第一个任务的图片路径和模型
            if i == 0:
                first_task_image_path = task['image_path']
                # 如果任务有model字段，则保存
                if 'model' in task.keys():
                    first_task_model = task['model']

        # 合并提示词
        merged_prompt = None
        if task_prompts:
            merged_prompt = " | ".join(task_prompts)
            if len(merged_prompt) > 500:  # 如果提示词太长，截断
                merged_prompt = merged_prompt[:497] + "..."

        # 创建新任务
        new_task_id = str(uuid.uuid4())

        # 创建新任务记录
        # 创建合并视频的任务消息
        merge_message = f'正在合成 {len(video_paths)} 个视频...'  # 更清晰的消息

        if first_task_image_path and first_task_model:
            # 如果有第一个任务的图片路径和模型，一起保存
            db.execute(
                'INSERT INTO tasks (id, status, message, image_path, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (new_task_id, 'merging_videos', merge_message, first_task_image_path, first_task_model, datetime.now().isoformat(), datetime.now().isoformat())
            )
        elif first_task_image_path:
            # 如果只有第一个任务的图片路径
            db.execute(
                'INSERT INTO tasks (id, status, message, image_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                (new_task_id, 'merging_videos', merge_message, first_task_image_path, datetime.now().isoformat(), datetime.now().isoformat())
            )
        else:
            # 如果没有第一个任务的图片路径
            db.execute(
                'INSERT INTO tasks (id, status, message, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                (new_task_id, 'merging_videos', merge_message, datetime.now().isoformat(), datetime.now().isoformat())
            )
        db.commit()

        # 启动后台线程合并视频
        def merge_videos_thread():
            try:
                with app.app_context():
                    # 合并视频
                    merged_path = merge_videos(video_paths)

                    if not merged_path:
                        update_task_status(new_task_id, 'failed', '合并视频失败')
                        return

                    # 更新任务状态和视频路径
                    update_task_status(new_task_id, 'completed', f'视频合成成功，合成了 {len(video_paths)} 个视频')
                    update_task_video_path(new_task_id, os.path.basename(merged_path))

                    # 如果有合并的提示词，更新任务提示词
                    if merged_prompt:
                        update_task_prompt(new_task_id, merged_prompt)
            except Exception as e:
                logger.error(f"合并视频线程出错: {str(e)}")
                with app.app_context():
                    update_task_status(new_task_id, 'failed', f'合并视频出错: {str(e)}')

        # 启动线程
        thread = threading.Thread(target=merge_videos_thread)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': '视频合并任务已提交',
            'task_id': new_task_id
        })

    except Exception as e:
        logger.error(f"合并视频API出错: {str(e)}")
        return jsonify({'error': f'合并视频出错: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>/open_folder', methods=['GET'])
def open_task_folder(task_id):
    """Open the folder containing task files."""
    try:
        # 获取任务信息
        db = get_db()
        task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

        if not task:
            return jsonify({'error': '任务不存在'}), 404

        # 确定要打开的文件夹
        folder_type = request.args.get('type', 'auto')
        folder_path = None

        if folder_type == 'image' or (folder_type == 'auto' and task['image_path']):
            # 打开图片所在文件夹
            folder_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
        elif folder_type == 'video' or (folder_type == 'auto' and task['video_path']):
            # 打开视频所在文件夹
            folder_path = os.path.abspath(app.config['OUTPUT_FOLDER'])
        else:
            # 默认打开输出文件夹
            folder_path = os.path.abspath(app.config['OUTPUT_FOLDER'])

        if not folder_path or not os.path.exists(folder_path):
            return jsonify({'error': '文件夹不存在'}), 404

        # 尝试打开文件夹
        try:
            # 根据操作系统选择打开文件夹的命令
            import platform
            import subprocess

            system = platform.system()
            if system == 'Windows':
                # Windows
                os.startfile(folder_path)
            elif system == 'Darwin':
                # macOS
                subprocess.call(['open', folder_path])
            else:
                # Linux
                subprocess.call(['xdg-open', folder_path])

            return jsonify({
                'success': True,
                'message': '已打开文件夹',
                'folder_path': folder_path
            })

        except Exception as e:
            logger.error(f"打开文件夹时出错: {str(e)}")
            return jsonify({'error': f'打开文件夹时出错: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"打开任务文件夹时出错: {str(e)}")
        return jsonify({'error': f'打开任务文件夹时出错: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
