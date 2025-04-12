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
   ```
   git clone <repository-url>
   cd siliconflow-i2v
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure your API key:
   Edit the `config.py` file and add your SiliconFlow API key.

## Usage

### Basic Usage

```
python main.py path/to/image.jpg
```

This will:
1. Process the image with VLM to identify its content
2. Refine the text into a prompt for I2V generation
3. Generate a video using the image as reference
4. Download the video to the output directory

### Advanced Usage

```
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
