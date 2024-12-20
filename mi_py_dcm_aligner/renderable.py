import pyvista as pv

class Renderable:    
    
    def poly_data(self) -> pv.PolyData:  
        raise NotImplementedError()    
