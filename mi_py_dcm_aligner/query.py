import pydantic 

class CmdQuery(pydantic.BaseModel):
    type: str  # Discriminator
    model_config = {"use_enum_values": True}  # Configuration to enable discriminator parsing

        
    def exec( self ) -> tuple[pydantic.BaseModel, str] | None:
        raise NotImplementedError()