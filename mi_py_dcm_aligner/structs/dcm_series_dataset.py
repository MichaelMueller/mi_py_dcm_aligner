from pydantic import BaseModel

class DcmSeriesDataSet(BaseModel):
    uids:list[str]
    files:list[ list[str] ]
    descriptions:list[str]