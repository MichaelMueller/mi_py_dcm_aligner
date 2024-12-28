from pydantic import BaseModel
from typing import Optional
from .dcm_series_dataset import DcmSeriesDataSet

class AlignArgs(DcmSeriesDataSet):    
    series_index:int
    dcm_output_folder:str=None,
    threshold:Optional[float]=None, 
    png_folder:Optional[str]=None