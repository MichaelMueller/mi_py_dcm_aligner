import os
import pydicom

from .dcm_series import DcmSeries
from .structs.dcm_series_dataset import DcmSeriesDataSet

class DcmStudy:
    
    def __init__(self, study_uid:str) -> None:
        self._study_uid = study_uid
        self._dcm_series:dict[str, DcmSeries] = {}
        
    def add_series( self, series:DcmSeries ) -> "DcmStudy":
        self._dcm_series[series.uid()] = series
   
    def series_uids( self ) -> list[str]:
        return list(self._dcm_series.keys())     
    
    def series_files( self ) -> list[list[str]]:
        files = []
        for series in self._dcm_series.values():
            files.append( series.file_paths() )
        return files
    
    def series_descriptions( self ) -> list[str]:
        descriptions = []
        for series in self._dcm_series.values():
            descriptions.append( series.description() )
        return descriptions        
        
    def series_data_set( self ) -> DcmSeriesDataSet:
        d = DcmSeriesDataSet(uids=self.series_uids(), files=self.series_files(), descriptions=self.series_descriptions())
        return d
        
    def get_series_at( self, idx:int ) -> "DcmSeries":
        return self._dcm_series[ list( self._dcm_series.keys() ) [idx] ]
    
    def get_series( self, series_uid:str ):
        if not series_uid in self._dcm_series:
            self._dcm_series[series_uid] = DcmSeries( series_uid )
        return self._dcm_series[series_uid]
        
    def uid( self ) -> str:
        return self._study_uid
    
    def description( self, default_val:str="" ) -> str:
        return self.get_series_at(0).get_file_at(0).meta_data().get( "StudyDescription", default_val )
    
    def __repr__(self) -> str:
        repr = f'Study {self._study_uid} / "{self.description()}":\n'
        for series in self._dcm_series.values():
            repr += str(series)
        repr = repr.replace("\n", "\n  ")
        return repr