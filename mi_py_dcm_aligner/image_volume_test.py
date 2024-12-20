import numpy as np

from .test import Test
from .create_transformation_matrix import CreateTransformationMatrix
from .image_volume import ImageVolume

class ImageVolumeTest( Test ):
    
    def __init__(self, parent: Test) -> None:
        super().__init__(parent)
        
    def _exec(self) -> bool | None:
        vol = ImageVolume( np.ones((3,3,3), dtype=np.uint8) )
        voxels = vol.data()
        
        self._check( voxels[0][0][0] == 1, f'voxels[0][0][0] == 1, got {voxels[0][0][0]}' )
        
        transformation_matrix = CreateTransformationMatrix((0,0,0), (3,3,3)).exec()
        vol = vol.apply_transformation( transformation_matrix )
        voxels = vol.data()
        
        self._check( voxels[0][0][0] == 0, f'voxels[0][0][0] == 0, got {voxels[0][0][0]}' )
        self._check( voxels[0][0][2] == 0, f'voxels[0][0][2] == 0, got {voxels[0][0][2]}' )
        self._check( voxels[3][3][3] == 1, f'voxels[3][3][3] == 1, got {voxels[3][3][3]}' )
        self._check( voxels[4][4][4] == 1, f'voxels[4][4][4] == 1, got {voxels[4][4][4]}' )
        self._check( voxels[5][5][5] == 1, f'voxels[5][5][5] == 1, got {voxels[5][5][5]}' )
        #self._check( voxels[5][5][0] == 0, f'voxels[5][0][0] == 0, got {voxels[5][5][0]}' )
        
        mini_cube_vol = ImageVolume( np.random.rand(2,2,2) )
        mini_cube = mini_cube_vol.data()
        transformation_matrix = np.array([
            [1, 0, 0, 1],  # Translation along x-axis
            [0, 1, 0, 1],   # Translation along y-axis
            [0, 0, 1, 1],  # Translation along z-axis
            [0, 0, 0, 1],
        ])
        # Apply the transformation
        mini_cube_translated_vol = mini_cube_vol.apply_transformation( transformation_matrix )
        mini_cube_translated = mini_cube_translated_vol.data()
        
        self._check( mini_cube_translated[2][2][2] == mini_cube[1][1][1], f'mini_cube_translated[2][2][2] == mini_cube[1][1][1]: {mini_cube_translated[2][2][2]} == {mini_cube[1][1][1]}' )
        
        transformation_matrix = CreateTransformationMatrix( angles=(90,0,0), translation=(0,0,0) ).exec()
        mini_cube_rotated_shifted_vol = mini_cube_vol.apply_transformation( transformation_matrix )
        mini_cube_rotated_shifted = mini_cube_rotated_shifted_vol.data()
        
        self._check( mini_cube_rotated_shifted[0][1][0] == mini_cube[0][0][0], f'mini_cube_rotated_shifted[0][1][0] == mini_cube[0][0][0]: {mini_cube_rotated_shifted[0][1][0]} == {mini_cube[0][0][0]}' )
        
        self._print("Testing LARGE volumes ...")
        
        volume = ImageVolume( np.random.rand(500,256,256) )
        self._timer_start()
        self._print("Applying transformation on LARGE volume ...")
        
        volume = volume.apply_transformation( transformation_matrix )
        self._timer_check( 10.0 )