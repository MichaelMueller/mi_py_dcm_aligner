

# built-in pythom modules
from inspect import signature
from typing import Callable, Union, Tuple, Literal, get_type_hints, Optional
import logging, sys, argparse, json, os, re
# pip modules
import pydantic
from pydantic import create_model

# local

Function = Callable[ [ pydantic.BaseModel ], Tuple[ pydantic.BaseModel, str ] | None ]

class CmdApp:
    
    def __init__(self, description:str) -> None:
        super().__init__()
        self._functions:dict[str, Function] = {}
        self._description = description
        
    def add_function( self, func_: Callable[ [ pydantic.BaseModel ], Tuple[ pydantic.BaseModel, str ] | None ], name:Optional[str]=None ) -> "CmdApp":
        if name == None:
            name = func_.__name__
        self._functions[name] = func_
        return self
    
    def remove_function( self, name:str ) -> "CmdApp":
        del self._functions[name]
        return self
        
    def exec(self) -> None:
        parser = argparse.ArgumentParser(description=self._description)
        parser.add_argument("input_json_file", type=str, help="Where to find the inputs serialized as json")
        parser.add_argument("-l", "--log_level", type=str, choices=["notset", "debug", "info", "warn", "error"], default="info", help="The basic log level")
        parser.add_argument("-lf", "--log_filter", type=str, default=None, help="A optional regex that removes matching log lines")
        if self._args == None:
            args = parser.parse_args()
        else:
            args = parser.parse_args(self._args)
        
        # Set up basic logging
        log_level = getattr(logging, args.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        
        # Set up regex!
        log_filter = args.log_filter
        if log_filter != None:
            class GlobalRegexFilter(logging.Filter):
                def __init__(self, pattern):
                    super().__init__()
                    self.pattern = re.compile(pattern)

                def filter(self, record):
                    # Suppress log messages that match the regex
                    return not self.pattern.search(record.getMessage())            
            logging.getLogger().addFilter(GlobalRegexFilter(log_filter))
        
        # Start reading inputs
        inputs_json_file = os.path.join( args.work_dir, args.inputs_file_name )        
        logging.debug(f'Trying to read inputs from {inputs_json_file}')
               
        # Check a valid name
        query_names = []
        for function_name in self._functions.keys():
            query_names.append( function_name )        
        
        class QueryBase(pydantic.BaseModel):
            name:Literal[tuple(query_names)] # type: ignore            
            class Config:
                allow_extra = True
                
        input_data:dict|None = {}
        nq:QueryBase|None = None
        with open( inputs_json_file, "r" ) as f:
            input_data:dict = json.load( f )
            logging.debug(f'Inputs:\n{json.dumps( input_data, indent=2)}')
            nq = QueryBase( input_data )
        
        # Check valid params
        func_ = self._functions[nq.name]
        args_type = next(iter(get_type_hints(func_).values()), None)
        class Query(pydantic.BaseModel):
            name:Literal[nq.name] # type: ignore 
            args:args_type # type: ignore
        
        q:Query = Query( **input_data )
        result = func_(q)        
        
        if result != None:
            data, file_path = result
            logging.info(f'writing outputs to {file_path}')
            with open(file_path, "w") as f:
                f.write( data.model_dump_json(indent=2))
                
        sys.exit(0)
        