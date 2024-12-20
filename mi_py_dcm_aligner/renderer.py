import numpy as np
import pyvista as pv
from .renderable import Renderable
from .image_volume import ImageVolume

class Renderer:
    def __init__(self) -> None:
        self._renderer = pv.Plotter()

    def add_renderable( self, r:Renderable, color:str="red", opacity:float=1.0) -> "Renderer":
        self._renderer.add_mesh( r.poly_data(), color=color, opacity=opacity)
        return self
    
    def add_image_volume( self, i:ImageVolume, cmap='viridis', opacity='sigmoid') -> "Renderer":
        volume_data = i.data()

        # Add the volume to the plotter with a colormap
        self._renderer.add_volume(volume_data, cmap=cmap, opacity=opacity)
        
        return self
    
    def add_lines( self, lines:np.ndarray|list, color:str="green", width:float=2.0) -> "Renderer":
        self._renderer.add_lines( np.array(lines) if type(lines) in [list, tuple] else lines, color=color, width=width  )
        return self
    
    def add_coord_sys( self, length:int|None=None) -> "Renderer":
        self._renderer.show_axes()
        
        if length != None:
            self.add_lines( [ (0,0,0), (length, 0, 0) ], color="red") \
                .add_lines( [ (0,0,0), (0, length, 0) ], color="green") \
                .add_lines( [ (0,0,0), (0, 0, length) ], color="blue")
        return self
    
    def add_points( self, points:np.ndarray, radius=1.0, color="red", label=None, opacity:float=1.0 ) -> "Renderer":
        for point in points:
            sphere = pv.Sphere(radius=radius, center=point)  # Create a sphere centered at each point
            self._renderer.add_mesh(sphere, color=color, label=label, opacity=opacity)
        return self
            
    def show(self) -> None:
        self._renderer.show()
