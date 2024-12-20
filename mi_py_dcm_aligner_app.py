import logging, sys, asyncio
from mi_py_dcm_aligner.app import App

if __name__ == "__main__":    
    asyncio.run( App().exec() )
    