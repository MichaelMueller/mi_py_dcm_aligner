from pydantic import BaseModel

class AlignArgs(BaseModel):
    uids:list[str]
    files:list[ list[str] ]
    descriptions:list[str]