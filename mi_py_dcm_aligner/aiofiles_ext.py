# built-in
import os, asyncio, tempfile
from pathlib import Path
from typing import Optional
import hashlib
# pip
from aiofiles.os import scandir
from pydantic import BaseModel

async def walk(directory):
    """
    Asynchronous version of os.walk using aiofiles.
    
    Args:
        directory (str): The root directory to traverse.
        
    Yields:
        tuple: (root, dirs, files) where:
               - root: Current directory path.
               - dirs: List of subdirectory names in the current directory.
               - files: List of file names in the current directory.
    """
    stack = [directory]

    while stack:
        current_dir = stack.pop()
        dirs = []
        files = []

        entries = await scandir(current_dir)
        for entry in entries:
            if entry.is_dir():
                dirs.append(entry.name)
                stack.append(Path(current_dir) / entry.name)
            elif entry.is_file():
                files.append(entry.name)

        yield current_dir, dirs, files
        
def hash_array(data: bytes, algorithm: str = "sha256") -> str:
    hash_func = hashlib.new(algorithm)
    hash_func.update(data)
    return hash_func.hexdigest()

async def async_hash_array(data: bytes, algorithm: str = "sha256"):
    return await asyncio.to_thread(hash_array, data, algorithm)

async def find_files_with_ext(dir:str, ext:Optional[str]=None) -> list[str]:
    """
    Find files in a directory with an optional extension filter.
    
    Args:
        dir (str): The directory to search.
        ext (str): The file extension to filter by.
        
    Returns:
        list: The list of file paths found.
    """
    files = []
    async for root, _, filenames in walk(dir):
        for filename in filenames:
            if ext is None or filename.endswith(ext):
                files.append( os.path.join(root, filename) )
    return files

async def create_temp_folder() -> "str":
    # Use tempfile.TemporaryDirectory for safe temporary folder creation
    loop = asyncio.get_event_loop()
    temp_dir = await loop.run_in_executor(None, tempfile.mkdtemp)
    return temp_dir