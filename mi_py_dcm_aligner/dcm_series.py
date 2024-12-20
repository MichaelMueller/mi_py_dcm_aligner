import os
from typing import Union
import pydicom
import SimpleITK as sitk

from .dcm_file import DcmFile
from .image_volume import ImageVolume

class DcmSeries:
    
    def __init__(self, series_uid:str) -> None:
        self._series_uid = series_uid
        self._dcm_files:dict[str, DcmFile] = {}
        self._sorted = False
        
    def add_dcm_file( self, file:DcmFile ) -> "DcmSeries":
        self._dcm_files[file.path()] = file
        self._sorted = False        
        return self
        
    def get_file( self, path:str ) -> DcmFile:
        return self._dcm_files[path]
        
    def get_file_at( self, idx:int ) -> DcmFile:
        return self._dcm_files[ list( self._dcm_files.keys() ) [idx] ]
    
    def num_files( self ) -> int:
        return len( self._dcm_files )

    def sort( self ) -> "DcmSeries":
        if self._sorted == False:
            self._dcm_files = dict( sorted( self._dcm_files.items(), key=lambda x: ( x[1].instance_number(), x[1].image_position_patient_z() ) ) ) 
            self._sorted = True
        return self        
    
    def description( self, default_val:str="" ) -> str:
        return self.get_file_at(0).meta_data().get( "SeriesDescription", default_val )
    
    def z_extents( self ) -> Union[float, None]:
        self.sort()
        first_z = self.get_file_at(0).image_position_patient_z(0)    
        last_z = self.get_file_at( self.num_files() ).image_position_patient_z(0)    
        return abs( last_z - first_z ) if last_z != None and first_z != None else None
    
    def avg_image_position_patient_z_distance( self, default:int|None=None, decimals:int|None=6 ) -> int|None:
        image_position_patient_z = 0
        last_image_position_patient_z = None
        self.sort()
        for file in self._dcm_files.values():
            
            curr_image_position_patient_z = file.image_position_patient_z(0)            
            if last_image_position_patient_z != None:
                image_position_patient_z = image_position_patient_z + (curr_image_position_patient_z - last_image_position_patient_z)
            last_image_position_patient_z = curr_image_position_patient_z
        
        image_position_patient_z = image_position_patient_z/len(self._dcm_files.values())
        
        if image_position_patient_z > 0:        
            if decimals != None:
                image_position_patient_z = round(image_position_patient_z, decimals)
            return image_position_patient_z
        else:
            return default      
        

    def file_paths(self) -> list[str]:      
        self.sort()                
        return [ file.path() for file in self._dcm_files.values() ]
        
    def uid( self ) -> str:
        return self._series_uid
        
    def first_file( self ) -> DcmFile:
        return self.get_file_at(0)
        
    def description( self ) -> str:
        return self.get_file_at(0).meta_data().get( "SeriesDescription", "No description" )
    
    def load_volume(self) -> tuple[ "ImageVolume", list[str]]:
        reader = sitk.ImageSeriesReader()
        files = self.file_paths()
        reader.SetFileNames(files)
        # Load the image and convert to numpy array
        image = reader.Execute()
        volume = sitk.GetArrayFromImage(image)  # Shape: (slices, height, width)
        return ImageVolume( volume ), files
    
    def __repr__(self) -> str:
        self.sort()
        repr = f'Series {self._series_uid} / "{self.description()}":\n'
        for dcm_file in self._dcm_files.values():
            repr += "  "+dcm_file.path()+"\n"
        return repr