# built-in imports
from typing import Tuple, Optional
import os, sys

# pip
import aioshutil, pydicom
from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn

# append current path to sys.path
parent_path = os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) )
if not parent_path in sys.path:
    sys.path.insert( 0, parent_path )
    
# local
from dicom import DcmSeriesDataSet, parse_dir, create_dicom_series, create_dcm_series_from_pngs
from aiofiles_ext import find_files_with_ext, create_temp_folder
from env import get_or_ask_and_wait_for_param
import image_3d_tools, log

class Args(DcmSeriesDataSet):    
    series_index:int
    series_description_suffix:str
    dcm_output_folder:Optional[str]=None
    threshold:Optional[float]=None
    
class Results(BaseModel):
    threshold:Optional[float]           = None
    matrix:list[list[float]]|None       = None
    rot_matrix:list[list[float]]|None   = None
    translation:list[float]|None        = None
    output_folder:Optional[str]         = None
    
async def align(args:Args) -> Results:
    
    # inputs
    png_folder = None
    try:        
        # load series             
        dcm_series = await create_dicom_series( args, args.series_index )
        volume = dcm_series.volume
        
        # threshold to get foreground object
        align_results = Results()      
        binary_volume, align_results.threshold = image_3d_tools.threshold(volume, binary_value=255, threshold_value=args.threshold)  
        
        # find rotated box around that object
        _, transformation_matrix = image_3d_tools.calculate_rotated_bounding_box(binary_volume)
        binary_volume = None
        align_results.matrix = transformation_matrix.tolist()
        align_results.rot_matrix = transformation_matrix[:3, :3].tolist()
        align_results.translation = transformation_matrix[:3, 3].tolist() 
                
        # transform image and write pngs        
        if args.dcm_output_folder != None:            
            volume = image_3d_tools.transform_image( volume, transformation_matrix )
            volume = image_3d_tools.trim_image( volume )
            png_folder = await image_3d_tools.save_slices_as_binary_images( volume)
            
            # TODO: write dcms
            template = dcm_series.datasets[ 0 ]

            series_desc = template.get("SeriesDescription", "")
            template.SeriesDescription = series_desc + args.series_description_suffix
            
            slice_thickness = dcm_series.slice_thickness or 0
            
            def per_instance_cb( idx:int, ds:pydicom.Dataset ):
                ds.ImagePositionPatient = [0, 0, idx * slice_thickness ]
                
            align_results.output_folder = await create_dcm_series_from_pngs( template, png_folder, args.dcm_output_folder, per_instance_cb=per_instance_cb )
            
        return align_results
    finally:
        if png_folder != None:
            await aioshutil.rmtree( png_folder )
        

def start_web_service():    
    # get env parameters
    host = get_or_ask_and_wait_for_param("HOST", default="127.0.0.1", value_type=str)
    port = get_or_ask_and_wait_for_param("PORT", default=8000, value_type=int)
    dev = get_or_ask_and_wait_for_param("DEV", default="False", value_type=lambda x: x.lower() == "true")
    log_level, _ = log.setup_from_env()
          
    module_name = os.path.splitext( os.path.basename(__file__) ) [0]
    app_string = module_name+":dev_web_service" if dev else module_name+":web_service"
    uvicorn.run(app_string, host=host, port=port, log_level=log_level, reload=dev)

def create_webservice( dev:bool=False ) -> FastAPI:
    # define the apps    
    web_service = FastAPI()
    web_service.get("/parse_dir", response_model=DcmSeriesDataSet)(parse_dir)
    web_service.post("/align", response_model=Results)(align)

    if dev:
        web_service.get("/find_files_with_ext", response_model=list[str])(find_files_with_ext)
    return web_service

# globals
web_service = create_webservice(False)
dev_web_service = create_webservice(True)

# main entry point
if __name__ == "__main__":
    start_web_service()