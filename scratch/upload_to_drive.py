#!/usr/bin/env python3
"""
Simple script to upload a file to Google Drive using the MCP tools
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the necessary paths to find our modules
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "core"))
sys.path.insert(0, str(Path(__file__).parent / "api"))

from api.thunderbird_drive import _get_drive_service, drive_upload_file


# Mock the MCP decorator
class MockMCP:
    def tool(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


async def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_to_drive.py <file_path> [folder_id]")
        print("Example: python upload_to_drive.py /path/to/file.html")
        sys.exit(1)

    local_path = sys.argv[1]
    folder_id = sys.argv[2] if len(sys.argv) > 2 else None
    file_name = sys.argv[3] if len(sys.argv) > 3 else None

    # Mock the MCP registration
    mcp = MockMCP()
    decorated_upload = mcp.tool()(drive_upload_file)

    print(f"Uploading {local_path} to Google Drive...")

    try:
        # Get the drive service first to ensure authentication
        _get_drive_service()

        # Call the upload function
        result = await decorated_upload(
            local_path=local_path, folder_id=folder_id, name=file_name
        )

        result_dict = json.loads(result)
        if "error" in result_dict:
            print(f"Error: {result_dict['error']}")
            sys.exit(1)

        print(f"Success! File uploaded to Google Drive")
        print(f"File ID: {result_dict['uploaded']['id']}")
        print(f"View link: {result_dict['uploaded']['webViewLink']}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
