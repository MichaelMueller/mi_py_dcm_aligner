# built-in pythom modules
import logging, sys, argparse, json, os
from typing import Optional
# pip modules
import pydicom    
import aioshutil
from mi_py_essentials import CliApp, Function, AsyncUtils#
from mi_py_essentials.packager import Packager
# local
from .dcm_dir import DcmDir
from .align_results import AlignResults
from .dcm_series import DcmSeries
from .dcm_series_dataset import DcmSeriesDataSet
from .functor import Functor    
from .create_dcm_series_from_pngs import CreateDcmSeriesFromPngs
from .renderer import Renderer
from .align_args import AlignArgs
from .align import Align

class App( Functor ):

    def __init__(self, args:list[str]|None=None) -> None:
        super().__init__()
        self._args = args
        
    async def package( self, output_zip="dist/mi_py_dcm_aligner.zip" ):
        args =  Packager.Args( output_zip=output_zip, requirements_file="requirements.txt", additional_files={ "README.md": "README.md" } )
        await Packager(args).exec()
        
    async def start_server( self,  host:str="127.0.0.1", port:int=8000, reload:bool=False ) -> None:
        from .web_service import Webservice
        webservice = Webservice( host=host, port=port, reload=reload )
        await webservice.exec()
        
    async def parse_dir( self, path:str, json_output_path:str ) -> None:
        dcm_folder = DcmDir( path ).parse()        
        series_data_set = dcm_folder.series_data_set()
        logging.info(f'Writing outputs to {json_output_path}')
        await AsyncUtils.write_json( json_output_path, series_data_set.model_dump() )
        
    async def render( self, series_data_set:DcmSeriesDataSet, series_index:int, coord_sys:Optional[float]=None, cmap:str="viridis", opacity:str='sigmoid' ) -> None:
        renderer = Renderer()
        series:DcmSeries = DcmSeries.from_dcm_series_dataset( series_data_set, series_index )        
        image, _ = series.load_volume() 
        if coord_sys != None:
            renderer.add_coord_sys( coord_sys )

        image = image.scale_z(5)
        renderer.add_image_volume( image, cmap=cmap, opacity=opacity )
        renderer.show()

    async def align( self, align_args:AlignArgs, align_result_file:str ) -> None:
        await Align( align_args, align_result_file ).exec()

        
    def description(self) -> str:            
        with open(os.path.dirname(__file__)+"/../README.md", "r") as file:
            return file.read().splitlines()[1]
        
    async def exec( self ) -> None:
        cli_app = CliApp( self.description() )
        cli_app.add_function( self.parse_dir )
        cli_app.add_function( self.align )
        cli_app.add_function( self.render )
        cli_app.add_function( self.start_server )
        cli_app.add_function( self.package )
        cli_app.set_default_function( "start_server" )
        await cli_app.exec()
        