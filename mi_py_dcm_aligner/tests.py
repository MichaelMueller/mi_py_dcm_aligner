import logging
from .test import Test    
from .image_volume_test import ImageVolumeTest    
    
class Tests( Test ):
    
    def __init__(self) -> None:
        super().__init__(None)
        
    def _exec(self) -> bool | None:
        return ImageVolumeTest( self ).exec()