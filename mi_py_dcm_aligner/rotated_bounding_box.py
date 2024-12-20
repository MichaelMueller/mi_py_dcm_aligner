from typing import TYPE_CHECKING
import logging, os, shutil

import numpy as np
from PIL import Image

from sklearn.decomposition import PCA
import pyvista as pv
from skimage.filters import threshold_otsu
from scipy.ndimage import zoom
if TYPE_CHECKING:
    from .image_volume import ImageVolume

class RotatedBoundingBox():    
    def __init__(self, volume:"ImageVolume") -> None:
        super().__init__()    
        self._volume = volume
        # internal
        self._corners:np.ndarray|None = None
        self._x_axis:np.ndarray|None = None
        self._y_axis:np.ndarray|None = None
        self._z_axis:np.ndarray|None = None
        self._transformation_matrix:np.ndarray|None = None
        
    def corners( self ) -> np.ndarray:
        self._assert_calculated()
        return self._corners
    
    def origin( self ) -> np.ndarray:
        self._assert_calculated()
        return self._corners[0]
    
    def x_axis( self ) -> np.ndarray:
        self._assert_calculated()
        
        return self._x_axis
        
    def y_axis( self ) -> np.ndarray:
        self._assert_calculated()
        
        return self._y_axis
    
    def z_axis( self ) -> np.ndarray:
        self._assert_calculated()
        
        return self._z_axis
    
    def local_to_world_transformation_matrix( self ) -> np.ndarray:
        self._assert_calculated()
        
        return self._transformation_matrix
    
    def recalculate(self) -> "RotatedBoundingBox":
        points = np.argwhere(self._volume.data())
        
        # Apply PCA to find the principal components (axes)
        pca = PCA(n_components=3)
        pca.fit(points)

        # Project points to PCA space
        transformed_points = pca.transform(points)

        # Find the axis-aligned bounding box in the PCA space
        min_point = np.min(transformed_points, axis=0)
        max_point = np.max(transformed_points, axis=0)

        # Create 8 corner points of the cuboid in the PCA space
        corners = np.array([[min_point[0], min_point[1], min_point[2]],
                            [min_point[0], min_point[1], max_point[2]],
                            [min_point[0], max_point[1], min_point[2]],
                            [min_point[0], max_point[1], max_point[2]],
                            [max_point[0], min_point[1], min_point[2]],
                            [max_point[0], min_point[1], max_point[2]],
                            [max_point[0], max_point[1], min_point[2]],
                            [max_point[0], max_point[1], max_point[2]]])

        # Transform the cuboid corners back to the original coordinate system
        cuboid_corners = pca.inverse_transform(corners)
        origin = cuboid_corners[0]
        # Ensure cuboid corners are float to avoid integer division issues
        f_cuboid_corners = cuboid_corners.astype(np.float64)
        
        # Define cuboid axes as vectors between adjacent corners
        x_axis_vector = f_cuboid_corners[4] - f_cuboid_corners[0]  # X-axis
        y_axis_vector = f_cuboid_corners[2] - f_cuboid_corners[0]  # Y-axis
        z_axis_vector = f_cuboid_corners[1] - f_cuboid_corners[0]  # Z-axis
                
        x_axis = x_axis_vector / np.linalg.norm(x_axis_vector)
        y_axis = y_axis_vector / np.linalg.norm(y_axis_vector)
        z_axis = z_axis_vector / np.linalg.norm(z_axis_vector)

        # Construct rotation matrix (R)
        rotation_matrix = np.column_stack((x_axis, y_axis, z_axis))

        # Compute the inverse of the rotation matrix (transpose for orthonormal basis)
        rotation_matrix_inv = rotation_matrix.T

        # Construct translation vector (T)
        translation_vector = -rotation_matrix_inv @ origin

        # Construct the 4x4 world-to-local transformation matrix
        transformation_matrix = np.eye(4)
        transformation_matrix[:3, :3] = rotation_matrix_inv
        transformation_matrix[:3, 3] = translation_vector
        
        self._corners = cuboid_corners
        self._x_axis = x_axis_vector
        self._y_axis = y_axis_vector
        self._z_axis = z_axis_vector
        self._transformation_matrix = transformation_matrix
        return self
        
    def _assert_calculated(self):
        if type(self._corners) != np.ndarray:
            self.recalculate()