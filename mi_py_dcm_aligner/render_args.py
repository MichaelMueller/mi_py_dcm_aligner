from pydantic import BaseModel

from .dcm_series_dataset import DcmSeriesDataSet

class RenderArgs(BaseModel):
    series_dataset:DcmSeriesDataSet
    series_index:int