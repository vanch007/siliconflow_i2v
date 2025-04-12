# SiliconFlow I2V Generator

This application uses SiliconFlow's models to generate videos from images. It processes an input image with a Vision Language Model (VLM) to identify its content, refines the text into a prompt, and generates a video using the Image-to-Video (I2V) model.

## Features

- Image content recognition using VLM
- Prompt refinement using LLM
- Video generation from images
- Video extension using the last frame
- Automatic video downloading

## Requirements

- Python 3.7+
- SiliconFlow API key

## Installation

1. Clone this repository:

   ```bash
   git clone <repository-url>
   cd siliconflow-i2v
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure your API key:
   Edit the `config.py` file and add your SiliconFlow API key.

## Usage

### Web Interface

The application provides a user-friendly web interface for generating videos:

```bash
python app.py
```

This will start a web server at [http://localhost:5001](http://localhost:5001). You can access the interface through your browser.

#### Web UI Features

1. Upload multiple images at once
2. Configure model parameters (VLM, LLM, I2V models)
3. Set generation options (negative prompt, video size, etc.)
4. Generate multiple videos per image
5. View task history and video previews
6. Regenerate videos from existing images
7. Create new videos from the last frame of existing videos

#### Step-by-Step Web UI Usage

1. **Start the application**:
   - Run `python app.py` in your terminal
   - Open your browser and navigate to [http://localhost:5001](http://localhost:5001)

2. **Configure API Key**:
   - Enter your SiliconFlow API key in the API Key field
   - Click the "Test" button to verify your API key works
   - Alternatively, click "Get Free API Key" to obtain a key from SiliconFlow

3. **Upload Images**:
   - Click the file upload area or drag and drop images
   - You can select multiple images at once
   - Uploaded images will appear as thumbnails

4. **Configure Generation Settings**:
   - Select the I2V model for video generation
   - Choose VLM model for image recognition
   - Choose LLM model for prompt refinement
   - Set the number of videos to generate per image
   - Optionally set a random seed for reproducible results
   - Customize the negative prompt if needed
   - Select video dimensions (portrait, landscape, or square)
   - Customize the style prompt to guide video generation
   - Optionally enable video extension using the last frame

5. **Generate Videos**:
   - Click the "Generate Video" button
   - A progress indicator will show the batch processing status
   - When complete, you'll be notified and can view the tasks

6. **View and Manage Tasks**:
   - Navigate to the "Task List" page to see all your tasks
   - Tasks are displayed in reverse chronological order
   - For completed tasks, you can:
     - Preview the generated videos
     - Regenerate videos with the same settings
     - Generate new videos from the last frame
     - Delete tasks and associated files

### Command Line Usage

#### Basic Usage

```bash
python main.py path/to/image.jpg
```

This will:

1. Process the image with VLM to identify its content
2. Refine the text into a prompt for I2V generation
3. Generate a video using the image as reference
4. Download the video to the output directory

#### Advanced Usage

```bash
python main.py path/to/image.jpg --output-dir custom/output --negative-prompt "poor quality, blurry" --image-size 1280x720 --seed 42 --extend
```

Options:

- `--output-dir`: Directory to save the output (default: "output")
- `--negative-prompt`: Negative prompt for video generation
- `--image-size`: Size of the video (e.g., 1280x720, 720x1280, 960x960)
- `--seed`: Random seed for generation
- `--extend`: Extend the video using the last frame

## Video Extension

The `--extend` option enables the video extension feature, which:

1. Extracts the last frame from the generated video
2. Uses this frame as a reference to generate a new video
3. Downloads the extended video

## Configuration

You can customize the application by editing the `config.py` file:

- `API_KEY`: Your SiliconFlow API key
- `VLM_MODEL`: Vision Language Model to use
- `LLM_MODEL`: Language Model for prompt refinement
- `I2V_MODEL`: Image to Video Model
- `DEFAULT_VIDEO_SIZE`: Default video resolution
- `DEFAULT_NEGATIVE_PROMPT`: Default negative prompt
- `OUTPUT_DIR`: Directory to save generated videos

## License

[MIT License](LICENSE)
