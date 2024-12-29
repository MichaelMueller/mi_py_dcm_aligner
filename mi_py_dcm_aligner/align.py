# built in
import tempfile
from typing import Optional
# pip
import numpy as np
import pydicom
import aioshutil
from mi_py_essentials import AsyncUtils
# local
from . import Functor, AlignArgs, AlignResults, DcmSeries, CreateDcmSeriesFromPngs

class Align(Functor):
    
    def __init__(self, args:AlignArgs, align_result_file:Optional[str]=None) -> None:
        super().__init__()
        self._args = args
        self._align_result_file = align_result_file
        
    async def exec(self) -> AlignResults:
        # inputs
        png_folder = self._args.png_folder or await AsyncUtils.create_temp_folder()

        if isinstance( png_folder, tempfile.TemporaryDirectory ):
            png_folder = png_folder.name
        
        # load series             
        series:DcmSeries = DcmSeries.from_dcm_series_dataset( self._args, self._args.series_index )
        image, dicom_files = series.load_volume()            
        
        # threshold      
        align_results = AlignResults()        
        binary_image, align_results.threshold = image.threshold(binary_value=255, threshold_value=self._args.threshold)
        
        # get matrix
        rotated_bounding_box = binary_image.rotated_bounding_box()
        transformation_matrix = rotated_bounding_box.local_to_world_transformation_matrix()
        align_results.matrix = transformation_matrix.tolist()#[[int(element) for element in row] for row in transformation_matrix]
        align_results.rot_matrix = transformation_matrix[:3, :3].tolist()
        align_results.translation = transformation_matrix[:3, 3].tolist()
                    
        # transform image and write pngs
        if self._args.dcm_output_folder != None:            
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
            CreateDcmSeriesFromPngs( template, png_folder=png_folder, output_folder=self._args.dcm_output_folder, clear_folder_if_it_exists=False, per_instance_cb=per_instance_cb ).exec()
            
            if remove_png_folder:
                await aioshutil.rmtree( png_folder )
        
        if self._align_result_file != None:
            await AsyncUtils.write( self._align_result_file, align_results.model_dump_json(indent=2) )
        
        return align_results