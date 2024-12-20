import logging
import numpy as np
from .functor import Functor
import numpy as np
from scipy.ndimage import affine_transform
from scipy.ndimage import map_coordinates

class ApplyTransformationToVolume(Functor):
    
    def __init__(self, image:np.ndarray, matrix:np.ndarray, interpolation_order=1) -> None:
        super().__init__()
        self._image = image
        self._matrix = matrix
        self._interpolation_order = interpolation_order
        
    def exec( self ) -> np.ndarray:
        return ApplyTransformationToVolume.transform_image( self._image, self._matrix, self._interpolation_order )

    def transform_points(points:np.ndarray, matrix:np.ndarray):
        
        # Convert points to homogeneous coordinates (Nx4)
        ones = np.ones((points.shape[0], 1))  # Column of ones for homogeneous coordinates
        points_homogeneous = np.hstack((points, ones))  # Append the ones
        
        # Apply the transformation matrix
        transformed_homogeneous = points_homogeneous @ matrix.T  # Matrix multiplication
        
        # Convert back to 3D (Nx3) by dropping the homogeneous coordinate
        transformed_points = transformed_homogeneous[:, :3]
        
        return transformed_points

    def transform_image(image:np.ndarray, matrix:np.ndarray, interpolation_order=3):
        
        bounding_box = np.array([
            [0, 0, 0],
            [image.shape[0], 0, 0],
            [0, image.shape[1], 0],
            [0, 0, image.shape[2]],
            [image.shape[0], image.shape[1], 0],
            [image.shape[0], 0, image.shape[2]],
            [0, image.shape[1], image.shape[2]],
            image.shape
        ])
        #logging.debug(f'bounding_box: {bounding_box}')
        
        transformed_bounding_box = ApplyTransformationToVolume.transform_points( bounding_box, matrix )
        #logging.debug(f'transformed_bounding_box: {transformed_bounding_box}')
        
        # Find minimum and maximum values for x, y, z
        min_coords = transformed_bounding_box.min(axis=0)  # Minimum x, y, z
        max_coords = transformed_bounding_box.max(axis=0)  # Maximum x, y, z

        #logging.debug(f"Minimum coordinates (x, y, z): {min_coords}")
        #logging.debug(f"Maximum coordinates (x, y, z): {max_coords}")
        
        transformed_image = affine_transform(
            image, 
            matrix=np.linalg.inv(matrix),
            offset=min_coords*-1, 
            output_shape=( int(max_coords[0])+1, int(max_coords[1])+1, int(max_coords[2])+1 ),
            order=interpolation_order
        )
        return transformed_image
