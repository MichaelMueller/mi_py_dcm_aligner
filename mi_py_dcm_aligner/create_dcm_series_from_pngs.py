import logging, os, shutil, datetime
from typing import Callable
import numpy as np
from PIL import Image
import pydicom, pydicom.uid

from .functor import Functor

class CreateDcmSeriesFromPngs(Functor):
    
    def __init__(self, template:str|pydicom.Dataset, png_folder:str, output_folder:str, clear_folder_if_it_exists:bool=False, per_instance_cb:Callable[[int,pydicom.Dataset], None]|None=None) -> None:
        super().__init__()
        self._template = template
        self._png_folder = png_folder
        self._output_folder = output_folder
        self._clear_folder_if_it_exists = clear_folder_if_it_exists
        self._per_instance_cb = per_instance_cb
        
    def exec(self) -> np.ndarray:
        """
        Creates a DICOM series from PNG slices.

        Args:
            png_folder (str): Path to the folder containing PNG images.
            output_folder (str): Path to the folder where DICOM files will be saved.
        """
        if type(self._template) == str:
            template = pydicom.dcmread(self._template, stop_before_pixels=True)
        else:
            template = self._template
        # Load PNG files and sort them by filename to ensure correct slice order
        png_folder = self._png_folder
        png_files = sorted([f for f in os.listdir(png_folder) if f.endswith('.png')])

        if not png_files:
            raise ValueError("No PNG files found in the specified folder.")

        # get common data
        # patient level
        
        # study level
        # study_instance_uid = template.get("StudyInstanceUID", pydicom.uid.generate_uid())
        # study_date = template.get( "StudyDate", datetime.datetime.now().strftime('%Y%m%d') ) 
        # study_time = template.get( "StudyTime", datetime.datetime.now().strftime('%H%M%S') ) 
        # study_id = "1"  # Example Study ID; modify as needed
        # series level
        # series_instance_uid = template.get("SeriesInstanceUID", pydicom.uid.generate_uid())
        # series_number = "1"  # Example Series Number; modify as needed
        template.SeriesNumber = template.SeriesNumber + 1
    
        # Delete output folder if it exists
        output_folder = self._output_folder
        if self._clear_folder_if_it_exists and os.path.exists(output_folder):
            shutil.rmtree(output_folder)
            
        os.makedirs(output_folder)
        
        for i, png_file in enumerate(png_files):
            # Load the image and convert to grayscale (if needed)
            img_path = os.path.join(png_folder, png_file)
            img = Image.open(img_path)
            logging.debug(f'found image with mode "{img.mode}" in {img_path}')
            pixel_array = np.array(img, dtype=np.uint16)  # Convert to 16-bit (DICOM standard)
            
            fileMeta = pydicom.Dataset()
            # fileMeta.MediaStorageSOPClassUID = pydicom._storage_sopclass_uids.SecondaryCaptureImageStorage 
            # ds.Modality = "OT"  # Other
            fileMeta.MediaStorageSOPClassUID = pydicom.uid.CTImageStorage
            
            fileMeta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
            fileMeta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
            #ds = FileDataset("", {},file_meta = fileMeta,preamble="\0"*128)
            ds = pydicom.Dataset()
            for key, value in template.items():
                ds[key] = value
            #ds = FileDataset("", {}, file_meta=fileMeta)
            ds.preamble=b"\0" * 128
            ds.file_meta = fileMeta
            ds.Modality = "CT"  # Other            

            # Add required DICOM attributes
            # ds.PatientName = "Anonymous^Anonymous"
            # ds.PatientID = "123456"
            # ds.PatientBirthDate = "19000101"  # Default value; modify as needed
            # ds.PatientSex = "O"  # Unknown
            # ds.Laterality = "R"
            
            # ds.StudyInstanceUID = study_instance_uid
            # ds.SeriesInstanceUID = series_instance_uid

            # ds.StudyDate = study_date
            # ds.StudyTime = study_time
            # ds.StudyID = study_id
            # ds.SeriesNumber = series_number
            # ds.AccessionNumber = "12345"  # Placeholder; should be updated
            # ds.InstitutionName = "Example Hospital"
            # ds.ReferringPhysicianName = "Referrer^Dr"
            # ds.Manufacturer = "Python Script"
            
            ds.SOPInstanceUID = fileMeta.MediaStorageSOPInstanceUID#pydicom.uid.generate_uid()
            ds.SOPClassUID = fileMeta.MediaStorageSOPClassUID
            ds.ImageType = ["ORIGINAL", "PRIMARY"]
            ds.ContentDate = datetime.datetime.now().strftime('%Y%m%d')
            ds.ContentTime = datetime.datetime.now().strftime('%H%M%S')
            ds.SoftwareVersions = "1.0"
            ds.Rows, ds.Columns = pixel_array.shape
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.BitsAllocated = 16
            ds.BitsStored = 16
            ds.HighBit = 15
            ds.PixelRepresentation = 0  # Unsigned integers
            ds.PixelData = pixel_array.tobytes()
            # Set slice-specific attributes
            ds.InstanceNumber = i + 1
            #ds.ImagePositionPatient = [0, 0, i]  # Simple example: slices 1mm apart
            #ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]  # Axial slices
            #ds.PixelSpacing = [1.0, 1.0]  # Assuming 1mm pixel spacing
            #ds.SliceThickness = 1.0  # Assuming 1mm slice thickness
            # ds.StudyDescription = "Example Study"
            # ds.SeriesDescription = "Example Series"
            # ds.PatientPosition = "HFS"  # Head First Supine
            
            if self._per_instance_cb != None:
                self._per_instance_cb( i, ds )

            # Save the DICOM file
            output_path = os.path.join(output_folder, f'slice_{i+1:03d}.dcm')
            pydicom.dataset.validate_file_meta(ds.file_meta, enforce_standard=True)
            ds.save_as(output_path, write_like_original=False)

        logging.debug(f"DICOM series created successfully in folder: {output_folder}")