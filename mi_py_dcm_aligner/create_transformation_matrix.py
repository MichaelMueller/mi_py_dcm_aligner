import numpy as np
from .functor import Functor

class CreateTransformationMatrix(Functor):
    
    def __init__(self, angles: tuple[float, float, float], translation: tuple[float, float, float]) -> None:
        super().__init__()
        self._angles = angles
        self._translation = translation
        
    def exec(self) -> np.ndarray:
        """
        Create a 4x4 affine transformation matrix with rotations and translation.
        """
        # Convert angles from degrees to radians
        rx, ry, rz = np.radians(self._angles)

        # Precompute sine and cosine values for all angles
        cos_rx, sin_rx = np.cos(rx), np.sin(rx)
        cos_ry, sin_ry = np.cos(ry), np.sin(ry)
        cos_rz, sin_rz = np.cos(rz), np.sin(rz)

        # Compute combined rotation matrix directly
        rotation_matrix = np.array([
            [
                cos_ry * cos_rz,
                -cos_ry * sin_rz,
                sin_ry,
            ],
            [
                sin_rx * sin_ry * cos_rz + cos_rx * sin_rz,
                -sin_rx * sin_ry * sin_rz + cos_rx * cos_rz,
                -sin_rx * cos_ry,
            ],
            [
                -cos_rx * sin_ry * cos_rz + sin_rx * sin_rz,
                cos_rx * sin_ry * sin_rz + sin_rx * cos_rz,
                cos_rx * cos_ry,
            ],
        ])

        # Construct the 4x4 transformation matrix
        transform_matrix = np.eye(4)
        transform_matrix[:3, :3] = rotation_matrix
        transform_matrix[:3, 3] = self._translation

        return transform_matrix