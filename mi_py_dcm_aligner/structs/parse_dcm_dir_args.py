from pydantic import BaseModel

class ParseDcmDirArgs(BaseModel):
    uids:list[str]
    files:list[ list[str] ]
    descriptions:list[str]