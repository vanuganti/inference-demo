# Cloud Inference Demo

This repository contains a cloud-based inference service demo, where multiple AI inference services can be compared. The service allows users to upload an image or audio file, provide a text prompt, and get inference results from various AI providers. The results are displayed in a clean, interactive interface.

### Features:
- **Multiple AI Services**: Supports multiple AI providers such as **OpenAI**, **GroQ**, **SambaNova**, **Together**, and **Cerebras**.
- **Image and Audio Input**: Users can upload image or audio files for inference.
- **Real-time Results**: Displays inference results dynamically as each service completes processing.
- **Result Visualization**: Results are displayed with tokens used, time taken, and the underlying model used.

### Table of Contents:
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Models Configuration](#models-configuration)
- [Contributing](#contributing)
- [License](#license)

## Technologies Used

- **Frontend**:
  - HTML, CSS, and JavaScript
  - Bootstrap for responsive layout
  - Highlight.js for code syntax highlighting
  - Marked.js for markdown parsing
  - DOMPurify for sanitizing HTML content

- **Backend**:
  - Flask (Python web framework)
  - aiohttp for asynchronous HTTP requests
  - APIs from various inference providers like OpenAI, GroQ, and SambaNova

## Installation

### Prerequisites
1. **Python 3.x**: Ensure you have Python installed.
2. **pip**: Python package installer.

### Clone the repository:
```bash
git clone https://github.com/yourusername/cloud-inference-demo.git
cd cloud-inference-demo
```

### Install dependencies:
- **Create a virtual environment and install the required packages**
```
python3 -m venv venv
source venv/bin/activate  # On Windows, use 'venv\Scripts\activate'
pip install -r requirements.txt
```

### Run the application:
```
python3 app.py
```
The application will start on http://localhost:5000.

### Model Changes
- ** Update models_config.json with correct models for text/vision/audio types for different inference solutions**

### Usage

. **Select Inference Services**: Choose the services you'd like to compare (e.g., OpenAI, GroQ, SambaNova, etc.).
. **Enter a Prompt**: Provide a text prompt for inference.
. **Upload Image or Audio (optional)**: Upload an image or audio file for inference.
. **Submit**: Click the submit button to send the request and receive results.
. **Results**: As each service finishes processing, the results will be displayed dynamically.


