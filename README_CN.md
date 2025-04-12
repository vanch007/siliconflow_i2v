# SiliconFlow 图生视频生成器

本应用程序使用SiliconFlow的模型从图像生成视频。它使用视觉语言模型(VLM)处理输入图像以识别其内容，将文本精炼为提示词，并使用图像到视频(I2V)模型生成视频。

## 功能特点

- 使用VLM进行图像内容识别
- 使用LLM进行提示词精炼
- 从图像生成视频
- 使用最后一帧延长视频
- 自动视频下载

## 系统要求

- Python 3.7+
- SiliconFlow API密钥

## 安装步骤

1. 克隆此仓库：
   ```
   git clone <仓库URL>
   cd siliconflow-i2v
   ```

2. 安装所需依赖：
   ```
   pip install -r requirements.txt
   ```

3. 配置您的API密钥：
   编辑`config.py`文件并添加您的SiliconFlow API密钥。

## 使用方法

### 基本用法

```
python main.py 图片路径/图片.jpg
```

这将：
1. 使用VLM处理图像以识别其内容
2. 将文本精炼为I2V生成的提示词
3. 使用图像作为参考生成视频
4. 将视频下载到输出目录

### 高级用法

```
python main.py 图片路径/图片.jpg --output-dir 自定义/输出 --negative-prompt "低质量，模糊" --image-size 1280x720 --seed 42 --extend
```

选项：
- `--output-dir`：保存输出的目录（默认："output"）
- `--negative-prompt`：视频生成的负面提示词
- `--image-size`：视频的尺寸（例如，1280x720，720x1280，960x960）
- `--seed`：生成的随机种子
- `--extend`：使用最后一帧延长视频

## 视频延长

`--extend`选项启用视频延长功能，它将：
1. 从生成的视频中提取最后一帧
2. 使用此帧作为参考生成新视频
3. 下载延长的视频

## 配置

您可以通过编辑`config.py`文件自定义应用程序：

- `API_KEY`：您的SiliconFlow API密钥
- `VLM_MODEL`：要使用的视觉语言模型
- `LLM_MODEL`：用于提示词精炼的语言模型
- `I2V_MODEL`：图像到视频模型
- `DEFAULT_VIDEO_SIZE`：默认视频分辨率
- `DEFAULT_NEGATIVE_PROMPT`：默认负面提示词
- `OUTPUT_DIR`：保存生成视频的目录

## 许可证

[MIT许可证](LICENSE)
