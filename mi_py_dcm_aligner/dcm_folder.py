from typing import Union, Optional
import os, logging
import pydicom
from pydicom.errors import InvalidDicomError

from .dcm_study import DcmStudy
from .dcm_series import DcmSeries
from .dcm_file import DcmFile
from .structs.dcm_series_dataset import DcmSeriesDataSet

class DcmFolder:
    
    def __init__(self, directory:str) -> None:
        self._directory = directory
        self._dcm_studies:dict[str, DcmStudy] = {}
        
    def series_uids( self ) -> list[str]:
        uids = []
        for study in self._dcm_studies.values():
            uids.extend( study.series_uids() )
        return uids

    def series_data_set( self ) -> DcmSeriesDataSet:
        d = None
        for study in self._dcm_studies.values():
            current_data_set = study.series_data_set()
            if d == None:
                d = current_data_set
            else:
                d.uids.extend( current_data_set.uids )
                d.files.extend( current_data_set.files )
                d.descriptions.extend( current_data_set.descriptions )
        return d       
    
    def series( self, uid:Optional[str] ) -> Union["DcmSeries", None]:
        if uid == None:
            return self.first_series()
        else:
            for study in self._dcm_studies.values():
                series = study.get_series( uid )
                if series:
                    return series
        return None
        
    def first_series(self) -> "DcmSeries":
        return self._dcm_studies[ list ( self._dcm_studies.keys() ) [0] ].get_series_at(0)
    
    def get_study( self, study_uid:str ) -> DcmStudy:
        if not study_uid in self._dcm_studies:
            self._dcm_studies[study_uid] = DcmStudy( study_uid )
        return self._dcm_studies[study_uid]
        
    def __repr__(self) -> str:
        repr = f"DICOM Folder {self._directory}\n"
        for study in self._dcm_studies.values():
            repr += str(study)
        
        repr = repr.replace("\n", "\n  ")
        return repr
    
    def parse(self) -> "DcmFolder":
        directory = self._directory
        self._dcm_studies = {}
        
        """
        Recursively walk through a directory, check for DICOM files, and load metadata (excluding pixel data).
        
        Args:
            directory (str): Path to the root directory.
        """
        logging.info(f'Starting parsing of dicoms in {directory}')
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Try to read the file as a DICOM file (skip pixel data)
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                    logging.debug(f'Found DICOM file "{file_path}"')
                    study_uid = ds.get("StudyInstanceUID")
                    series_uid = ds.get("SeriesInstanceUID")
                    # Print basic metadata (customize as needed)
                    dcm_file = DcmFile(file_path, ds)
                    self.get_study( study_uid ).get_series( series_uid ).add_dcm_file(dcm_file)
                    
                except InvalidDicomError:
                    # Skip non-DICOM files
                    pass
                except Exception as e:
                    # Handle other exceptions (e.g., permission issues)
                    logging.warning(f"Error processing file {file_path}: {e}")
                    
        return self