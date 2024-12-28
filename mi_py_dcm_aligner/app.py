# built-in pythom modules
import logging, sys, argparse, json, os
from typing import Optional
# pip modules
import pydicom    
import aioshutil
from mi_py_essentials import CliApp, Function, AsyncUtils
# local
from .dcm_dir import DcmDir
from .dcm_align_results import DcmAlignResults
from .dcm_series import DcmSeries
from .dcm_series_dataset import DcmSeriesDataSet
from .functor import Functor    
from .create_dcm_series_from_pngs import CreateDcmSeriesFromPngs
from .render_args import RenderArgs
from .renderer import Renderer

class App( Functor ):

    def __init__(self, args:list[str]|None=None) -> None:
        super().__init__()
        self._args = args
        
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

    async def dcm_align( self,
                        dcm_series_json_file:str, 
                        series_idx:int, 
                        dcm_align_result_file:str,
                        dcm_output_folder:str=None,
                        threshold:Optional[float]=None, 
                        png_folder:Optional[str]=None ) -> None:
        # inputs
        png_folder = png_folder or await AsyncUtils.create_temp_folder()
        
        # load series             
        dcm_series_data_set = DcmSeriesDataSet.model_validate_json( await AsyncUtils.read( dcm_series_json_file) )
        series:DcmSeries = DcmSeries.from_dcm_series_dataset( dcm_series_data_set, series_idx )
        image, dicom_files = series.load_volume()            
        
        # threshold      
        dcm_align_results = DcmAlignResults()        
        binary_image, dcm_align_results.threshold = image.threshold(binary_value=255, threshold_value=threshold)
        
        # get matrix
        rotated_bounding_box = binary_image.rotated_bounding_box()
        transformation_matrix = rotated_bounding_box.local_to_world_transformation_matrix()
        dcm_align_results.matrix = transformation_matrix.tolist()#[[int(element) for element in row] for row in transformation_matrix]
        dcm_align_results.rot_matrix = transformation_matrix[:3, :3].tolist()
        dcm_align_results.translation = transformation_matrix[:3, 3].tolist()
                    
        # transform image and write pngs
        if dcm_output_folder != None:            
            image = image.transform( transformation_matrix ).trim()
            remove_png_folder = png_folder == None
            png_folder = png_folder or str(await AsyncUtils.create_temp_folder())
            image.save_slices_as_binary_images( png_folder, clear_folder_if_exists=False)

            # write dcms (TODO)
            avg_image_position_patient_z_distance = series.avg_image_position_patient_z_distance()
            template = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)
            series_desc = template.get("SeriesDescription", None)
            template.SeriesDescription = ("" if series_desc == None else series_desc + " - ") + "Aligned Object"
            template.SliceThickness = avg_image_position_patient_z_distance
            def per_instance_cb( idx:int, ds:pydicom.Dataset ):
                ds.ImagePositionPatient = [0, 0, idx*avg_image_position_patient_z_distance]
            CreateDcmSeriesFromPngs( template, png_folder=png_folder, output_folder=dcm_output_folder, clear_folder_if_it_exists=False, per_instance_cb=per_instance_cb ).exec()
            
            if remove_png_folder:
                await aioshutil.rmtree( png_folder )
            
        await AsyncUtils.write( dcm_align_result_file, dcm_align_results.model_dump_json(indent=2) )
        
    def description(self) -> str:            
        with open(os.path.dirname(__file__)+"/../README.md", "r") as file:
            return file.read().splitlines()[1]
        
    async def exec( self ) -> None:
        cli_app = CliApp( self.description() )
        cli_app.add_function( self.parse_dir )
        cli_app.add_function( self.dcm_align )
        cli_app.add_function( self.render )
        await cli_app.exec()
        