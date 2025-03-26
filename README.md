# YouTube MCP Server

A Model Context Protocol (MCP) server that provides tools for searching YouTube videos, retrieving transcripts, and performing semantic search over video content.

## Support Us

If you find this project helpful and would like to support future projects, consider buying us a coffee! Your support helps us continue building innovative AI solutions.

<a href="https://www.buymeacoffee.com/blazzmocompany"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=&slug=blazzmocompany&button_colour=40DCA5&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00"></a>

Your contributions go a long way in fueling our passion for creating intelligent and user-friendly applications.

## Table of Contents

- [YouTube MCP Server](#youtube-mcp-server)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Server](#running-the-server)
  - [1. Direct Method](#1-direct-method)
  - [2. Configure for Claude.app](#2-configure-for-claudeapp)
- [Available Tools](#available-tools)
- [Using with MCP Clients](#using-with-mcp-clients)
  - [Example Usage](#example-usage)
- [Debugging](#debugging)
- [Contributing](#contributing)
- [License](#license)

## Features

- Search YouTube videos without using the official API
- Retrieve video transcripts
- Store video information and transcripts in a vector database
- Perform semantic search over stored video transcripts

## Prerequisites

- Python 3.8+
- Google API key for embeddings
- uv package manager

## Installation

1. Clone this repository

2. Create and activate a virtual environment using uv:
```bash
uv venv
# On Windows:
.venv\Scripts\activate
# On Unix/MacOS:
source .venv/bin/activate
```

3. Install dependencies using uv:
```bash
uv pip install -r requirements.txt
```

4. Create a `.env` file with your Google API key:
```
GOOGLE_API_KEY=your_api_key_here
```

## Running the Server

There are two ways to run the MCP server:

### 1. Direct Method

To start the MCP server directly:

```bash
uv run python server.py
```

### 2. Configure for Claude.app

Add to your Claude settings without using any package manager this works for windows:
```json
"mcpServers": {
  "youtube": {
    "command": "C:\\Path\\To\\Your\\Project\\.venv\\Scripts\\python.exe",
    "args": ["C:\\Path\\To\\Your\\Project\\server.py"],
    "env": {
      "GOOGLE_API_KEY": "your_api_key_here"
    }
  }
}
```

Using Uv package manager this works for windows:

```json
"mcpServers": {
  "youtube": {
    "command": "uv",
    "args": ["--directory", "C:\\Path\\To\\Your\\Project", "run", "server.py"],
    "env": {
      "GOOGLE_API_KEY": "your_api_key_here"
    }
  }
}
```

## Available Tools

The server provides the following tools:

1. `search-youtube`: Search for YouTube videos based on a query
   - Parameters:
     - query: Search query string
     - max_results: Maximum number of results to return (default: 5)

2. `get-transcript`: Get the transcript of a YouTube video
   - Parameters:
     - video_url: URL of the YouTube video

3. `store-video-info`: Store video information and transcript in the vector database
   - Parameters:
     - video_url: URL of the YouTube video
     - metadata: Optional metadata about the video

4. `search-transcripts`: Search stored video transcripts using semantic search
   - Parameters:
     - query: Search query
     - limit: Maximum number of results to return (default: 3)

## Using with MCP Clients

This server can be used with any MCP-compatible client, such as Claude Desktop App. The tools will be automatically discovered and made available to the client.

### Example Usage

1. Start the server using one of the methods described above
2. Open Claude Desktop App
3. Look for the hammer icon to verify that the YouTube tools are available
4. You can now use commands like:
   - "Search for Python tutorial videos"
   - "Get the transcript of this video: [video_url]"
   - "Search through stored video transcripts about machine learning"

## Debugging

If you encounter any issues:

1. Make sure your Google API key is correctly set in the `.env` file
2. Check that all dependencies are installed correctly
3. Verify that the server is running and listening for connections
4. Look for any error messages in the server output

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.