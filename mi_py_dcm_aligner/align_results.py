from typing import Tuple
from pydantic import BaseModel

Vec = Tuple[float, float, float]
HomVec = Tuple[float, float, float, float]

class AlignResults(BaseModel):
    threshold:float|None=None
    matrix:list[list[float]]|None = None
    rot_matrix:list[list[float]]|None = None
    translation:list[float]|None=None