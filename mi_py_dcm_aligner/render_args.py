from pydantic import BaseModel
from typing import Optional
from .dcm_series_dataset import DcmSeriesDataSet

class RenderArgs(DcmSeriesDataSet):
    series_index:int
    coord_sys_length:Optional[float] = None