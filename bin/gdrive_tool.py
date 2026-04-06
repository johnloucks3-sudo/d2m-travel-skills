"""
gdrive_tool.py - A simple CLI wrapper for thunderbird_drive.py functions.
"""
import argparse
import asyncio
from pathlib import Path

# We need to add the parent directory to the path to allow the import
import sys
sys.path.append(str(Path(__file__).resolve().parent))

from thunderbird_drive import drive_download_file, _get_drive_service

# Mock the MCP tool registration to allow direct function calls
class MockMCP:
    def tool(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

async def main():
    parser = argparse.ArgumentParser(description="CLI for Google Drive operations.")
    parser.add_argument("--download", required=True, help="Google Drive file ID to download.")
    parser.add_argument("--out", required=True, help="Local file path to save the downloaded file.")
    
    args = parser.parse_args()

    # The drive functions are async, so we need to run them in an event loop.
    # We also need to mock the registration decorator.
    mcp = MockMCP()
    
    # Manually decorate the function to align with its original definition
    decorated_download = mcp.tool()(drive_download_file)

    print(f"Attempting to download file ID {args.download} to {args.out}...")
    result = await decorated_download(file_id=args.download, local_path=args.out)
    print(result)

if __name__ == "__main__":
    # Ensure the drive service is initialized before running the async main
    try:
        _get_drive_service()
        asyncio.run(main())
    except Exception as e:
        print(f"An error occurred: {e}")

