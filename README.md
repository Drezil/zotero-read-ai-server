# README for Read-AI

## Overview

**Read-AI** is a server-based application designed to handle and process HTTP requests for text summarization tasks. The server integrates with an AI model (e.g., Ollama) to generate concise, structured summaries from raw text inputs. The summaries are stored for later retrieval or further use.

---

## Features

- **Text Summarization**: Processes and summarizes text content, supporting a variety of input formats.
- **AI Integration**: Utilizes the Ollama model for high-quality text analysis and summarization.
- **HTTP Server**: Serves as an HTTP endpoint for handling client requests.
- **Threaded Processing**: Uses a queue to manage and process multiple requests concurrently.
- **Flexible Configurations**: Adjustable parameters for server settings, verbosity, and model selection.

---

## Prerequisites

- Python 3.11
- `poetry` for dependency management
- Additional Python libraries (see [Dependencies](#dependencies))

---

## Installation

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd read-ai
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Ensure all additional dependencies (e.g., `flash-attn`, `ollama`) are installed.

---

## Usage

### Running the Server

To start the server, use the following command:

```bash
poetry run python ./server.py -- --verbose
```

### Command-Line Arguments

- `-b, --bind`: Host to bind to (default: `0.0.0.0`).
- `-p, --port`: Port to listen on (default: `3246`).
- `--ollama-host`: Host of the Ollama server (default: `localhost`).
- `--ollama-port`: Port of the Ollama server (default: `11434`).
- `--ollama-model`: AI model for summarization (default: `phi3:14b-medium-128k-instruct-f16`).
- `-v, --verbose`: Increase output verbosity.
- `-q, --quiet`: Suppress all output (overrides `--verbose`).

---

## Dependencies

The following dependencies are required:

- `numpy==1.24.4`
- `pillow==10.3.0`
- `requests`
- `torch>=2.3.0,<2.4.0`
- `torchvision==0.18.0`
- `transformers==4.40.2`
- `flash-attn` (specific wheel provided in the `pyproject.toml`)
- `ollama==0.3.1`
- `setuptools>68.0.0`
- Development: `wheel>=0.43.0`

---

## File Structure

- `server.py`: Main application server script.
- `pyproject.toml`: Project configuration and dependencies.
- `summaries/`: Directory to store generated summaries.
- `errors/`: Directory for logging failed processes.

---

## Contributions

Contributions are welcome, but are conditional on accepting the Contributor
License Agreement. Read the [CONTRIBUTING.md](CONTRIBUTING.md) for details. Please follow these steps:

1. Fork the repository.
2. Create a feature branch.
3. Submit a pull request with detailed information about your changes.

---

## License

This project is licensed under the AGPLv3 license. See the LICENSE file for details.
