import logging, os, shutil

import numpy as np
from PIL import Image

from sklearn.decomposition import PCA
import pyvista as pv
from skimage.filters import threshold_otsu
from scipy.ndimage import zoom

from .renderable import Renderable
from .rotated_bounding_box import RotatedBoundingBox
from .apply_transformation_to_volume import ApplyTransformationToVolume

class ImageVolume(Renderable):
    
    def create_binary_pyramid(base_length) -> tuple["ImageVolume", int]:
        """
        Creates a 3D binary pyramid image volume with a definable base length.
        
        Parameters:
            base_length (int): The length of the square base of the pyramid. Must be odd for symmetry.
            
        Returns:
            numpy.ndarray: A 3D binary array with a pyramid structure.
        """
        if base_length % 2 == 0:
            raise ValueError("Base length must be an odd integer for a symmetric pyramid.")
        
        height = (base_length + 1) // 2
        volume = np.zeros((height, base_length, base_length), dtype=np.uint8)
        
        for z in range(height):
            start = z
            end = base_length - z
            volume[z, start:end, start:end] = 1
        
        return ImageVolume(volume), height

    
    def __init__(self, data:np.ndarray) -> None:
        super().__init__()    
        self._data = data
        
    def data(self) -> np.ndarray:
        return self._data

    def scale_z( self, scale_factor_z:float, order=3 ) -> "ImageVolume":
        scaling_factors = (scale_factor_z, 1.0, 1.0)

        # Apply the zoom function
        stretched_volume = zoom(self._data, scaling_factors, order=order)  # Use 'order=3' for cubic interpolation

        return ImageVolume( stretched_volume )     

    def poly_data(self) -> pv.PolyData:      
        grid = pv.PolyData(np.argwhere(self._data))
        grid.point_data["values"] = np.ones(len(grid.points))
        surface = grid.delaunay_3d().extract_geometry()
        return surface
     
    def scale( self, scale_factors:tuple[float, float, float] ) -> "ImageVolume":
        # Rescale the array
        scaled_array = zoom(self.data(), zoom=scale_factors)
        return ImageVolume( scaled_array )
        
    def transform(self, matrix:np.ndarray, interpolation_order=3) -> "ImageVolume":
        func_ = ApplyTransformationToVolume( self.data(), matrix, interpolation_order)
        return ImageVolume( func_.exec() )
    
    def trim(self) -> "ImageVolume":
        volume = self.data()
        # Find the indices of non-zero elements
        non_zero_indices = np.argwhere(volume != 0)

        # Get the bounding box coordinates
        min_coords = non_zero_indices.min(axis=0)  # Minimum along each dimension
        max_coords = non_zero_indices.max(axis=0) + 1  # Maximum along each dimension (inclusive)

        # Slice the volume to the bounding box
        trimmed_volume = volume[
            min_coords[0]:max_coords[0],
            min_coords[1]:max_coords[1],
            min_coords[2]:max_coords[2]
        ]

        return ImageVolume( trimmed_volume )

    def rotated_bounding_box(self) -> RotatedBoundingBox:
        return RotatedBoundingBox(self)

    def get_rotated_bounding_box( self ):
        points = np.argwhere(self.data())
        
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
        
        return cuboid_corners, x_axis_vector, y_axis_vector, z_axis_vector, transformation_matrix
    
    def threshold(self, threshold_value: float = None, binary_value:int=1) -> tuple["ImageVolume", float]:
        # Apply Otsu's threshold to create a binary volume
        volume = self.data()
        binary_image = np.zeros_like(volume, dtype=np.uint8)
        if threshold_value == None:
            threshold_value = threshold_otsu(volume)
            logging.debug(f'Otsu threshold:{threshold_value}')
        
        binary_image[volume > threshold_value] = binary_value
            
        return ImageVolume( binary_image ), float(threshold_value)
    
    def save_slices_as_binary_images(self, folder, step_size=1, clear_folder_if_exists=False):
        """
        Creates binary slices of the 3D object along the z-axis and saves them as PNG images.

        Parameters:
            volume (numpy.ndarray): The 3D binary array.
            folder (str): The folder to save the PNG images.
            step_size (int): Step size for slicing.
        """
        # Remove the folder if it exists, then create it
        if clear_folder_if_exists == True and os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder, exist_ok=True)

        logging.debug(f'creating slices in folder {folder}')
        volume = self.data()
        # Determine the bit depth based on the volume data type
        if volume.dtype == np.uint8:
            mode = 'L'  # 8-bit grayscale
        elif volume.dtype == np.uint16:
            mode = 'I;16'  # 16-bit grayscale
            logging.debug(f'Got uin16 image')
        else:
            raise ValueError(f"Unsupported data type: {volume.dtype}")

        c_width=None
        c_height=None
        # Iterate through the z-axis with the given step size
        for z in range(0, volume.shape[0], step_size):
            slice_ = volume[z, :, :]
            if volume.dtype == np.bool_:
                # Convert binary data to uint8 (0 or 255)
                img = (slice_ * 255).astype(np.uint8)
            else:
                img = slice_  # Use the slice as is for supported data types
            
            # Create the image
            image = Image.fromarray(img, mode=mode)
            
            if c_width != image.width or c_height != image.height:
                print(f'Slice width: {image.width}, height: {image.height}')
                c_width, c_height = image.width, image.height
            
            # Save the image
            filename = os.path.join(folder, f"slice_{z:03}.png")
            image.save(filename)
            
        logging.debug(f"Slices saved in folder: {folder}")