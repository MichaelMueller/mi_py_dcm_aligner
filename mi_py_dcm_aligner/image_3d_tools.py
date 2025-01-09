# built-in
from typing import Tuple
import logging, pydicom, os, asyncio

# pip
import aiofiles.os
import aioshutil
import pydicom
from pydicom.errors import InvalidDicomError
from pydicom.filebase import DicomBytesIO
from pydantic import BaseModel
import SimpleITK as sitk
import numpy as np
from skimage.filters import threshold_otsu
from sklearn.decomposition import PCA
from scipy.ndimage import affine_transform
from PIL import Image

# local
from aiofiles_ext import walk, create_temp_folder

def threshold(volume:np.ndarray, threshold_value: float = None, binary_value:int=1) -> Tuple[np.ndarray, float]:
        # Apply Otsu's threshold to create a binary volume
        binary_image = np.zeros_like(volume, dtype=np.uint8)
        if threshold_value == None:
            threshold_value = threshold_otsu(volume)
            logging.debug(f'Otsu threshold:{threshold_value}')
        
        binary_image[volume > threshold_value] = binary_value
            
        return binary_image, float(threshold_value)
    
def calculate_rotated_bounding_box(binary_volume:np.ndarray) -> Tuple[np.ndarray, np.ndarray]: 
    points = np.argwhere(binary_volume)

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

    return cuboid_corners, transformation_matrix


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
    
    transformed_bounding_box = transform_points( bounding_box, matrix )
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

def trim_image(volume:np.ndarray) -> np.ndarray:
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

    return trimmed_volume
    
async def save_slices_as_binary_images(volume:np.ndarray, step_size:int=1) -> str:
    
    folder = await create_temp_folder()

    logging.debug(f'creating slices in folder {folder}')
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
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, image.save, filename)

    logging.debug(f"Slices saved in folder: {folder}")
    return folder