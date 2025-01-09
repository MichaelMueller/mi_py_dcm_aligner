import os, aiofiles.os, asyncio
# pip
import aioconsole
from dotenv import load_dotenv
from aiofiles import open as aio_open

# public interface
async def get_or_ask_for_param(param_name, default=None, value_type=str):
    return await _get_or_ask_for_param(param_name, default, value_type)

def get_or_ask_and_wait_for_param(param_name, default=None, value_type=str):
    return asyncio.run(_get_or_ask_for_param(param_name, default, value_type))

# private vars
_dot_env_loaded = False

async def _get_or_ask_for_param(param_name, default=None, value_type=str):
    """
    Get a parameter from the environment. If not found, ask the user for it.
    Args:
        param_name (str): The name of the environment variable.
        default: The default value if the variable is not found.
        value_type: The expected type (str, int, bool).
    Returns:
        The value of the parameter, converted to the specified type.
    """
    global _dot_env_loaded
    if not _dot_env_loaded:
        await _load_dotenv_async()
        _dot_env_loaded = True
        
    value = os.getenv(param_name)
    if value is None:
        # Ask the user for input if not in .env
        user_input = await aioconsole.ainput(f"Enter value for {param_name} (default: {default}): ") or default
        try:
            value = value_type(user_input)
        except ValueError:
            print(f"Invalid value. Expected {value_type.__name__}.")
            exit(1)

        # Save to .env file
        async with aio_open(".env", "a") as env_file:
            await env_file.write(f"{param_name}={user_input}\n")

    else:
        value = value_type(value)

    return value

async def _load_dotenv_async(dotenv_path=".env"):
    """
    Asynchronously load environment variables from a .env file.
    """
    try:
        async with aio_open(dotenv_path, mode="r") as file:
            async for line in file:
                # Remove comments and whitespace
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass