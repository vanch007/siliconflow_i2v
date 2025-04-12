"""
Functions for merging multiple videos.
"""

import os
import uuid
import logging
import subprocess
from datetime import datetime
from config import OUTPUT_DIR
from utils import ensure_directory_exists, generate_timestamp

logger = logging.getLogger(__name__)

def merge_videos(video_paths, output_dir=OUTPUT_DIR):
    """
    Merge multiple videos into a single video.

    Args:
        video_paths (list): List of paths to the videos to merge
        output_dir (str, optional): Directory to save the merged video

    Returns:
        str: Path to the merged video, or None if merging failed
    """
    try:
        # 记录输入参数
        logger.info(f"开始合并视频，视频数量: {len(video_paths)}")
        logger.info(f"输出目录: {output_dir}")
        for i, path in enumerate(video_paths):
            logger.info(f"视频 {i+1}: {path} (存在: {os.path.exists(path)})")
        # 确保输出目录存在
        ensure_directory_exists(output_dir)

        # 生成带时间戳的输出文件名
        timestamp = generate_timestamp()
        output_filename = f"merged_{timestamp}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        # 创建临时文件列表
        import tempfile
        # 创建一个临时文件
        temp_fd, temp_list_path = tempfile.mkstemp(suffix='.txt', prefix='ffmpeg_list_')
        os.close(temp_fd)  # 关闭文件描述符，稍后我们会自己打开文件

        # 确保输出目录存在
        ensure_directory_exists(output_dir)

        logger.info(f"创建临时文件列表: {temp_list_path}")

        with open(temp_list_path, 'w') as f:
            for video_path in video_paths:
                # 使用视频文件的绝对路径
                video_abs_path = os.path.abspath(video_path)
                f.write(f"file '{video_abs_path}'\n")
                logger.info(f"添加视频到列表: {video_abs_path}")

        # 使用 FFmpeg 合并视频
        # 获取ffmpeg路径
        try:
            from flask import current_app
            ffmpeg_path = current_app.config.get('FFMPEG_PATH', 'ffmpeg')
        except Exception:
            ffmpeg_path = 'ffmpeg'  # 默认值

        # 生成输出文件的绝对路径
        output_abs_path = os.path.abspath(output_path)

        # 使用绝对路径构建命令
        cmd = [
            ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', temp_list_path,  # 使用临时文件列表的路径
            '-c', 'copy',
            output_abs_path  # 使用输出文件的绝对路径
        ]

        logger.info(f"执行命令: {' '.join(cmd)}")

        # 检查ffmpeg是否存在
        try:
            # 尝试使用应用程序配置中的ffmpeg路径
            from flask import current_app
            ffmpeg_path = current_app.config.get('FFMPEG_PATH', 'ffmpeg')
            logger.info(f"使用ffmpeg路径: {ffmpeg_path}")

            # 尝试运行ffmpeg -version来检查是否存在
            subprocess.run([ffmpeg_path, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("ffmpeg不存在或无法运行，请安装ffmpeg")
            return None
        except Exception as e:
            logger.error(f"检查ffmpeg时出错: {str(e)}")
            return None

        # 执行命令 - 使用绝对路径，不需要设置工作目录
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            # 不设置 cwd，因为我们使用了绝对路径
        )

        stdout, stderr = process.communicate()

        # 删除临时文件
        if os.path.exists(temp_list_path):
            os.remove(temp_list_path)
            logger.info(f"删除临时文件: {temp_list_path}")

        # 检查命令是否成功执行
        if process.returncode != 0:
            logger.error(f"合并视频失败: {stderr.decode('utf-8')}")
            # 记录更多调试信息
            logger.error(f"视频路径列表: {video_paths}")
            logger.error(f"视频绝对路径列表: {[os.path.abspath(p) for p in video_paths]}")
            logger.error(f"临时文件列表路径: {temp_list_path}")
            logger.error(f"输出文件路径: {output_abs_path}")
            logger.error(f"ffmpeg命令: {' '.join(cmd)}")
            return None

        logger.info(f"视频合并成功: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"合并视频时出错: {str(e)}")
        return None
