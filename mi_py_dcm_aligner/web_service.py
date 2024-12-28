# built-in pythom modules
import logging, asyncio
from typing import Optional, Dict
# pip modules
from fastapi import FastAPI, Request
from uvicorn import Config, Server
# local
from .functor import Functor
from .align_args import AlignArgs

class Webservice( Functor ):

    def __init__(self, host:str="127.0.0.1", port:int=8000, reload:bool=False) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._reload = reload

    async def align(self, request: Request) -> Dict:
            body = await request.json()
            alignment_request = AlignArgs(**body)  # Validate using the Pydantic model


            return {"hello_world": "hello_world"}

    async def exec( self ) -> None:
        app = FastAPI()
        # Add the route programmatically
        app.add_api_route(
            path="/align",  # Endpoint path
            endpoint=self.align,  # Function to call
            methods=["POST"],  # HTTP methods
        )
                
        async def run_uvicorn():
            config = Config(app=app, host=self._host, port=self._port, reload=self._reload)
            server = Server(config)

            # Check if the server should be started
            if not server.should_exit:
                await server.serve()
                
        logging.info(f"Starting server at {self._host}:{self._port}")
        await run_uvicorn()