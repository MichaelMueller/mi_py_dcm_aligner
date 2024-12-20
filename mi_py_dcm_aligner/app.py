# built-in pythom modules
import logging, sys, argparse, json, os
# pip modules
import pydicom    
from mi_py_essentials import CliApp, Function, Util
# local
from .dcm_dir import DcmDir
from .functor import Functor    
from .create_dcm_series_from_pngs import CreateDcmSeriesFromPngs

class App( Functor ):

    def __init__(self, args:list[str]|None=None) -> None:
        super().__init__()
        self._args = args
        
    async def parse_dcm_dir( self, path:str, json_output_path:str ) -> None:
        dcm_folder = DcmDir( path ).parse()        
        series_data_set = dcm_folder.series_data_set()
        logging.info(f'Writing outputs to {json_output_path}')
        await Util.write_json( json_output_path, series_data_set.model_dump() )
        
    def description(self) -> str:            
        with open(os.path.dirname(__file__)+"/../README.md", "r") as file:
            return file.read().splitlines()[1]
        
    async def exec( self ) -> None:
        cli_app = CliApp( self.description() )
        cli_app.add_function( self.parse_dcm_dir )
        await cli_app.exec()
        
    # def exec(self) -> None:
    #     desc = self.parse_description_from_readme()
    #     parser = argparse.ArgumentParser(description=desc)
    #     parser.add_argument("work_dir", type=str, help=f'This directory is used to read the inputs file and potentially write the outputs file')
    #     parser.add_argument("-i", "--inputs_file_name", type=str, default="inputs.json", help="File name for the inputs")
    #     parser.add_argument("-o", "--outputs_file_name", type=str, default="outputs.json", help="File name for the outputs")
    #     parser.add_argument("-l", "--log_level", type=str, choices=["notset", "debug", "info", "warn", "error"], default="info", help="log lvel")
    #     if self._args == None:
    #         args = parser.parse_args()
    #     else:
    #         args = parser.parse_args(self._args)
        
    #     # Set up logging with the specified level
    #     log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    #     logging.basicConfig(level=log_level)
    
    #     inputs_json_file = args.work_dir + "/" + args.inputs_file_name
    #     outputs_json_file = args.work_dir + "/" + args.outputs_file_name
        
    #     logging.info(f'trying to read inputs from {inputs_json_file}')
    #     with open( inputs_json_file, "r" ) as f:
    #         inputs:dict = json.load( f )
    #         logging.info(f'Inputs:\n{json.dumps( inputs, indent=2)}')
        
    #     outputs = None
    #     # function switch
    #     if inputs["function"] == "find_dcm_series":
    #         dcm_dir_path = inputs["dcm_dir"]
    #         from .dcm_folder import DcmFolder
    #         dcm_folder = DcmFolder( dcm_dir_path ).parse()
    #         outputs = dcm_folder.series_data_set().dict()
        
    #     if inputs["function"] == "align":
    #         # inputs
    #         dcm_dir_path = inputs.get("dcm_dir", None)
    #         dcm_series_files = inputs.get("dcm_series_files", [])
    #         assert os.path.isdir( dcm_dir_path ) or len( dcm_series_files ) > 0
            
    #         series_uid = inputs.get("series_uid", None)     
    #         threshold_value = inputs.get("threshold_value", None)      
    #         png_folder = inputs.get("png_folder", None)   
    #         clear_png_folder_if_exists = inputs.get("clear_png_folder_if_exists", False) 
    #         dcm_output_folder = inputs.get("dcm_output_folder", None)   
    #         clear_dcm_output_folder_if_exists = inputs.get("clear_dcm_output_folder_if_exists", False) 
    #         outputs = {}
            
    #         # load series
    #         from .dcm_folder import DcmFolder
    #         dcm_dir = DcmFolder( dcm_dir_path ).parse()             
    #         series = dcm_dir.series( series_uid )
    #         image, dicom_files = series.load_volume()            
            
    #         # threshold      
    #         binary_image, threshold_value = image.threshold(binary_value=255, threshold_value=threshold_value)
    #         outputs["threshold_value"] = threshold_value
            
    #         # get matrix
    #         rotated_bounding_box = binary_image.rotated_bounding_box()
    #         transformation_matrix = rotated_bounding_box.local_to_world_transformation_matrix()
    #         outputs["transformation_matrix"] = transformation_matrix.tolist()#[[int(element) for element in row] for row in transformation_matrix]
                       
    #         # transform image and write pngs
    #         if png_folder != None:            
    #             image = image.transform( transformation_matrix ).trim()
    #             image.save_slices_as_binary_images( png_folder, clear_folder_if_exists=clear_png_folder_if_exists)

    #             # write dcms (TODO)
    #             if dcm_output_folder != None:
    #                 avg_image_position_patient_z_distance = series.avg_image_position_patient_z_distance()
    #                 template = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)
    #                 series_desc = template.get("SeriesDescription", None)
    #                 template.SeriesDescription = ("" if series_desc == None else series_desc + " - ") + "Aligned Object"
    #                 template.SliceThickness = avg_image_position_patient_z_distance
    #                 def per_instance_cb( idx:int, ds:pydicom.Dataset ):
    #                     ds.ImagePositionPatient = [0, 0, idx*avg_image_position_patient_z_distance]
    #                 CreateDcmSeriesFromPngs( template, png_folder=png_folder, output_folder=dcm_output_folder, clear_folder_if_it_exists=clear_dcm_output_folder_if_exists, per_instance_cb=per_instance_cb ).exec()
            
    #     if outputs != None:
    #         logging.info(f'writing outputs to {outputs_json_file}')
    #         with open(outputs_json_file, "w") as f:
    #             json.dump(outputs, f, indent=2)
                
    #     sys.exit(0)
        