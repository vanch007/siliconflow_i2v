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

   ```bash
   git clone https://github.com/vanch007/siliconflow_i2v.git
   cd siliconflow-i2v
   ```

2. 安装所需依赖：

   ```bash
   pip install -r requirements.txt
   ```

3. 配置您的API密钥（选择一种方式）：

   **方式一：使用环境变量（推荐）**
   - 复制`.env.example`文件并重命名为`.env`
   - 编辑`.env`文件，添加您的SiliconFlow API密钥：

     ```bash
     SILICONFLOW_API_KEY=your_api_key_here
     ```

   - 注意：`.env`文件不会被提交到Git仓库，因此您的API密钥将保持安全

   **方式二：通过Web界面输入**
   - 启动应用程序后，在Web界面中输入您的API密钥
   - API密钥将存储在浏览器的localStorage中，不会被提交到服务器

   **方式三：编辑配置文件（不推荐）**
   - 编辑`config.py`文件并添加您的SiliconFlow API密钥
   - 注意：这种方式可能会将您的API密钥提交到Git仓库，除非您将`config.py`添加到`.gitignore`文件中

## 使用方法

### Web界面

本应用程序提供了一个用户友好的Web界面用于生成视频：

```bash
python app.py
```

这将在 [http://localhost:5001](http://localhost:5001) 启动一个Web服务器。您可以通过浏览器访问该界面。

#### Web界面功能

1. 一次上传多张图片
2. 配置模型参数（VLM、LLM、I2V模型）
3. 设置生成选项（负面提示词、视频尺寸等）
4. 为每张图片生成多个视频
5. 查看任务历史和视频预览
6. 从现有图片重新生成视频
7. 从现有视频的最后一帧创建新视频

#### Web界面使用步骤

1. **启动应用程序**：
   - 在终端中运行 `python app.py`
   - 打开浏览器并访问 [http://localhost:5001](http://localhost:5001)

2. **配置API密钥**：
   - 在API Key字段中输入您的SiliconFlow API密钥
   - 点击"测试"按钮验证您的API密钥是否有效
   - 或者点击"获取免费API Key"从 SiliconFlow 获取密钥

3. **上传图片**：
   - 点击文件上传区域或拖放图片
   - 您可以一次选择多张图片
   - 上传的图片将显示为缩略图

4. **配置生成设置**：
   - 选择用于视频生成的I2V模型
   - 选择用于图像识别的VLM模型
   - 选择用于提示词精炼的LLM模型
   - 设置每张图片生成的视频数量
   - 可选择设置随机种子以获得可重现的结果
   - 根据需要自定义负面提示词
   - 选择视频尺寸（竖屏、横屏或方形）
   - 自定义风格提示词指导视频生成
   - 可选择启用使用最后一帧延长视频

5. **生成视频**：
   - 点击"生成视频"按钮
   - 进度指示器将显示批处理状态
   - 完成后，您将收到通知并可以查看任务

6. **查看和管理任务**：
   - 导航到"任务列表"页面查看所有任务
   - 任务按时间倒序显示（最新的在前）
   - 对于已完成的任务，您可以：
     - 预览生成的视频
     - 使用相同设置重新生成视频
     - 从最后一帧生成新视频
     - 删除任务及相关文件

### 命令行使用

#### 基本用法

```bash
python main.py 图片路径/图片.jpg
```

这将：

1. 使用VLM处理图像以识别其内容
2. 将文本精炼为I2V生成的提示词
3. 使用图像作为参考生成视频
4. 将视频下载到输出目录

#### 高级用法

```bash
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
