import os
import pydicom

class DcmFile:
    
    def __init__(self, path:str, meta_data:pydicom.Dataset) -> None:
        self._path = path
        self._meta_data = meta_data
        
    def path( self ) -> str:
        return self._path        

    def meta_data( self ) -> pydicom.Dataset:
        return self._meta_data                
    
    def instance_number( self, default_val:int|None=None ) -> str:
        return self.meta_data().get( "InstanceNumber", default_val )
    
    def image_position_patient( self, default_val:tuple[float,float,float]|None=None ) -> str:
        return self.meta_data().get( "ImagePositionPatient", default_val )
    
    def slice_thickness( self, default_val:int|None=None ) -> str:
        return self.meta_data().get( "SliceThickness", default_val )
    
    def image_position_patient_z( self, default_val:int|None=None ) -> str:
        ipp = self.image_position_patient()
        if ipp != None:
            return ipp[2]
        else:
            return default_val