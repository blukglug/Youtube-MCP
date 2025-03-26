import os, sys
from typing import List
from mcp.server import Server
from mcp.types import Tool, TextContent, ListToolsResult, INVALID_PARAMS
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from langchain_community.tools import YouTubeSearchTool
from langchain_community.document_loaders import YoutubeLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import lancedb
import asyncio
from dotenv import load_dotenv
import logging
from datetime import datetime

DATA_DIR = "./data"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)

# Silence noisy third-party loggers
for logger_name in ["asyncio", "urllib3.connectionpool", "mcp.server.lowlevel.server"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Get current date for log filename
log_filename = datetime.now().strftime('%d-%m-%y') + '.log'
log_filepath = os.path.join(DATA_DIR, log_filename)

# Configure our application logger with proper formatting
logger = logging.getLogger("youtube-mcp")
logger.setLevel(logging.DEBUG)  # Set our logger to DEBUG level
logger.propagate = False  # Prevent double logging

# Create a formatter with proper newlines
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create and add console handler
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Create and add file handler for logging to file
file_handler = logging.FileHandler(log_filepath)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

load_dotenv()

async def serve(read, write, options):
    """Run the YouTube MCP server."""
    logger.info("Initializing YouTube MCP Server")
    server = Server(name="youtube-mcp-server")
    logger.debug("Created MCP Server instance")
    
    youtube_search = YouTubeSearchTool()
    logger.debug("Initialized YouTube Search Tool")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        task_type="retrieval_document"  # Set default task type for document storage
    )
    logger.debug("Initialized Google Generative AI Embeddings")
    
    db = lancedb.connect('youtube_db')
    logger.debug("Connected to LanceDB database")
    
    # Create videos table if it doesn't exist
    try:
        videos_table = db.open_table("videos")
        logger.debug("Opened existing videos table")
    except:
        import pyarrow as pa
        videos_table = db.create_table(
            "videos",
            schema=pa.schema([
                pa.field("id", pa.string(), nullable=False),
                pa.field("text", pa.string()),
                pa.field("metadata", pa.struct([]), nullable=True),  # JSON field as struct
                pa.field("vector", pa.list_(pa.float32(), 768))  # Fixed-size list for vector
            ]),
            mode="create"
        )
        logger.debug("Created new videos table")
    
    def clean_text(text: str) -> str:
        """Clean text to remove problematic characters."""
        try:
            # Replace emojis and special characters with their text equivalents
            # or remove them if no good replacement exists
            return text.encode('ascii', 'ignore').decode('ascii')
        except Exception:
            return str(text)

    # Register the list_tools handler
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """Handle listing available tools"""
        logger.info("Handling list_tools request")
        tools = [
            Tool(
                name="search-youtube",
                description="Search for YouTube videos based on a query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"},
                        "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 5}
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="get-transcript",
                description="Get the transcript of a YouTube video",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "video_url": {"type": "string", "description": "URL of the YouTube video"}
                    },
                    "required": ["video_url"]
                }
            ),
            Tool(
                name="store-video-info",
                description="Store video information and transcript in the vector database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "video_url": {"type": "string", "description": "URL of the YouTube video"},
                        "metadata": {"type": "object", "description": "Optional metadata about the video"}
                    },
                    "required": ["video_url"]
                }
            ),
            Tool(
                name="search-transcripts",
                description="Search stored video transcripts using semantic search",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Maximum number of results to return", "default": 3}
                    },
                    "required": ["query"]
                }
            )
        ]
        logger.debug(f"Returning {len(tools)} tools: {[tool.name for tool in tools]}")
        return tools

    # Register the call_tool handler
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            logger.info(f"Handling tool call: {name} with arguments: {arguments}")

            if name == "search-youtube":
                max_results = int(arguments.get("max_results", 5))
                results = youtube_search.run(f"{arguments['query']},{max_results}")
                # Properly parse and clean results
                parsed_results = eval(results)  # Consider using json.loads() if results are JSON
                cleaned_results = clean_text(str(parsed_results))
                return [TextContent(type="text", text=cleaned_results)]
            
            elif name == "get-transcript":
                languages = ["en", "es", "fr", "pt", "it", "id", "de", "zh", "ko", "ja", "ar", "hi", "bn", "sw", "yo"]  # English, Spanish, French, Portuguese, Italian, Indonesian, German, Chinese, Korean, Japanese, Arabic, Hindi, Bengali, Swahili, Yoruba
                # Extract video_id from URL, handling URLs with additional parameters
                video_url = arguments["video_url"] if len(arguments["video_url"].split("&")) == 1 else arguments["video_url"].split("&")[0]  # Extract video_id from URL when the url is like https://www.youtube.com/watch?v=VIDEO_ID&...
                # Use YoutubeLoader with languages parameter
                loader = YoutubeLoader.from_youtube_url(
                    youtube_url=video_url,
                    language=languages,
                    add_video_info=False,
                    continue_on_failure=True
                )
                # Load transcript and extract text
                documents = loader.load()
                if documents:
                    transcript_text = documents[0].page_content
                    cleaned_transcript = clean_text(transcript_text)
                    return [TextContent(type="text", text=cleaned_transcript)]
                else:
                    return [TextContent(type="text", text="No transcript found for this video.")]
            
            elif name == "store-video-info":
                languages = ["en", "es", "fr", "pt", "it", "id", "de", "zh", "ko", "ja", "ar", "hi", "bn", "sw", "yo"]
                # Extract video_id from URL, handling URLs with additional parameters
                video_url = arguments["video_url"] if len(arguments["video_url"].split("&")) == 1 else arguments["video_url"].split("&")[0]  # Extract video_id from URL when the url is like https://www.youtube.com/watch?v=VIDEO_ID&...
                # Use YoutubeLoader with languages parameter
                loader = YoutubeLoader.from_youtube_url(
                    youtube_url=video_url,
                    language=languages,
                    add_video_info=True,
                    continue_on_failure=True
                )
                # Load transcript and extract text
                documents = loader.load()
                if documents:
                    transcript_text = documents[0].page_content
                    cleaned_content = clean_text(transcript_text)
                    vector = embeddings.embed_documents(
                        [cleaned_content],
                        task_type="retrieval_document"
                    )[0]
                    # Use provided metadata and add video metadata from document if available
                    cleaned_metadata = {
                        k: clean_text(str(v)) if isinstance(v, str) else v
                        for k, v in arguments.get("metadata", {}).items()
                    }
                    # Add video_id to metadata
                    cleaned_metadata["video_id"] = YoutubeLoader.extract_video_id(youtube_url=video_url)
                    videos_table.add([{
                        "id": video_url,
                        "text": cleaned_content,
                        "metadata": cleaned_metadata,
                        "vector": vector
                    }])
                    return [TextContent(type="text", text=f"Successfully stored video information for {cleaned_metadata.get('video_id')}")]
                else:
                    return [TextContent(type="text", text="No transcript found for this video.")]
                
            elif name == "search-transcripts":
                query_vector = embeddings.embed_query(
                    arguments["query"],
                    task_type="retrieval_query"
                )
                results = videos_table.search(
                    query_vector
                ).limit(int(arguments.get("limit", 3))).to_pandas()
                
                formatted_results = []
                for result in results.itertuples():
                    formatted_results.append({
                        "video_url": result.id,
                        "metadata": getattr(result, "metadata", {}),
                        "text_sample": result.text[:200] + "..." if len(result.text) > 200 else result.text,
                        "score": float(getattr(result, "_4", 0.0))  # LanceDB score is in the last column
                    })
                return [TextContent(type="text", text=str(formatted_results))]
                
            else:
                raise ValueError(f"Unknown tool: {name}")
                
        except Exception as e:
            logger.error(f"Error handling tool call: {e}", exc_info=True)
            raise McpError(INVALID_PARAMS, str(e))

    # Create initialization options
    options = server.create_initialization_options()
    logger.debug(f"Created initialization options: {options}")
    
    # Properly use stdio_server as an async context manager
    await server.run(read, write, options, raise_exceptions=True)

async def main():
    try:
        logger.info("Starting YouTube MCP Server...")
        options = {
            "protocolVersion": "0.1.0",
            "capabilities": {}
        }
        async with stdio_server() as (read, write):
            await serve(read, write, options)
    except KeyboardInterrupt:
        logger.info("Server shutting down gracefully...")
        print("\nServer shutting down gracefully...", file=sys.stderr)
    except Exception as e:
        logger.error(f"Fatal error occurred: {e}", exc_info=True)
        print(f"\nFatal error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutting down...")
