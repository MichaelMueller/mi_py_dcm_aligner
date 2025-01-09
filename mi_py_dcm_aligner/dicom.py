# built-in
from typing import Optional, Callable, Tuple, Dict
import logging, pydicom, os, asyncio, datetime

# pip
import aiofiles.os
import pydicom
from pydicom.errors import InvalidDicomError
from pydicom.filebase import DicomBytesIO
from pydantic import BaseModel
from dataclasses import dataclass
import SimpleITK as sitk
import numpy as np
from PIL import Image
import pydicom, pydicom.uid

# local
import aiofiles_ext

PixelSpacing = Tuple[float, float]|None

class DcmSeriesDataSet(BaseModel):
    uids:list[str|None]=[]
    files:list[ list[str] ]=[]
    descriptions:list[str|None]=[]
    slice_thicknesses:list[float|None]=[]
    pixel_spacings:list[PixelSpacing]=[]

@dataclass
class DicomSeries:
    files:list[str] # sorted!!!
    datasets:Dict[str, pydicom.Dataset]
    volume:Optional[np.ndarray]
    slice_thickness:float|None=None
    pixel_spacing:PixelSpacing=None
    
async def load_dcm( file_path:str, stop_before_pixels:bool=False ) -> pydicom.Dataset:
    async with aiofiles.open(file_path, mode="rb") as f:
        data = await f.read()  # Asynchronously read the file contents                
        # Use DicomBytesIO to wrap the binary data and read it into a pydicom dataset
        dataset = pydicom.dcmread(DicomBytesIO(data), stop_before_pixels=stop_before_pixels)
        return dataset   
    
async def async_save_as(dataset: pydicom.Dataset, filename: str, enforce_file_format:bool=True):
    # Write the dataset to a DicomBytesIO stream
    with DicomBytesIO() as buffer:
        dataset.save_as(buffer, enforce_file_format=enforce_file_format)
        buffer.seek(0)  # Ensure the buffer is at the start
        
        # Asynchronously write to the file using aiofiles
        async with aiofiles.open(filename, 'wb') as f:
            await f.write(buffer.read())
            
async def parse_dir( directory:str ) -> DcmSeriesDataSet:             
    series_data_set = DcmSeriesDataSet()
    # directory = args.dir
    
    logging.info(f'Starting parsing of dicoms in {directory}')
    async for root, _, files in aiofiles_ext.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # Try to read the file as a DICOM file (skip pixel data)
                dataset = await load_dcm(file_path, stop_before_pixels=True)
                logging.debug(f'Found DICOM file "{file_path}"')
                # study_uid = ds.get("StudyInstanceUID")
                series_uid = dataset.get("SeriesInstanceUID", "")
                series_description = dataset.get("SeriesDescription", "")
                pixel_spacing = dataset.get("PixelSpacing", None)
                if pixel_spacing != None:                    
                    pixel_spacing = tuple(map(float, pixel_spacing))
                    
                slice_thickness = dataset.get("SliceThickness", None)
                                        
                if not series_uid in series_data_set.uids:
                    series_data_set.uids.append(series_uid)
                    series_data_set.descriptions.append(series_description)
                    series_data_set.pixel_spacings.append(pixel_spacing)
                    series_data_set.slice_thicknesses.append(slice_thickness)
                    series_data_set.files.append([])
                    series_idx = len(series_data_set.uids) - 1
                else:
                    series_idx = series_data_set.uids.index(series_uid)
                series_data_set.files[series_idx].append(file_path)
                
            except InvalidDicomError:
                # Skip non-DICOM files
                pass
            except Exception as e:
                # Handle other exceptions (e.g., permission issues)
                logging.warning(f"Error processing file {file_path}: {e}")
                
    return series_data_set

async def create_dicom_series( series_data_set:DcmSeriesDataSet, idx:int ) -> DicomSeries:
    # use instance number and alternatively image position patient z to sort the files
    files = series_data_set.files[idx]
    file_to_dataset = { file: await load_dcm(file, stop_before_pixels=True) for file in files }
    file_to_dataset = dict( sorted( file_to_dataset.items(), key=lambda x: (x[1].get("InstanceNumber", 0), x[1].get("ImagePositionPatient", [0, 0, 0])[2]) ) )
    
    files = list( file_to_dataset.keys() )
    slice_thickness = series_data_set.slice_thicknesses[idx]
    pixel_spacing = series_data_set.pixel_spacings[idx]
    
    def load_volume_sync( sorted_series_files:list[str] ) -> np.ndarray:            
        reader = sitk.ImageSeriesReader()
        reader.SetFileNames(sorted_series_files)
        # Load the image and convert to numpy array
        image = reader.Execute()
        volume = sitk.GetArrayFromImage(image)  # Shape: (slices, height, width)
        return volume    
    
    loop = asyncio.get_event_loop()
    volume:np.ndarray = await loop.run_in_executor(None, load_volume_sync, files)
    return DicomSeries(files=files, datasets=list(file_to_dataset.values()), volume=volume, slice_thickness=slice_thickness, pixel_spacing=pixel_spacing)


async def create_dcm_series_from_pngs( template:str|pydicom.Dataset, png_folder:str, output_folder:str, per_instance_cb:Callable[[int,pydicom.Dataset], None]|None=None) -> str:
    """
    Creates a DICOM series from PNG slices.

    Args:
        png_folder (str): Path to the folder containing PNG images.
        output_folder (str): Path to the folder where DICOM files will be saved.
    """
    if type(template) == str:
        template = await load_dcm(template, stop_before_pixels=True)
    else:
        template = template
    # Load PNG files and sort them by filename to ensure correct slice order
    png_folder = png_folder
    png_files = sorted([f for f in await aiofiles.os.listdir(png_folder) if f.endswith('.png')])

    if not png_files:
        raise ValueError("No PNG files found in the specified folder.")

    template.SeriesNumber = template.SeriesNumber + 1
    template.SeriesInstanceUID = pydicom.uid.generate_uid()
    
    output_folder = output_folder + "/" + template.SeriesInstanceUID
    
    await aiofiles.os.makedirs(output_folder, exist_ok=True)
    
    for i, png_file in enumerate(png_files):
        # Load the image and convert to grayscale (if needed)
        img_path = os.path.join(png_folder, png_file)
        img = Image.open(img_path)
        logging.debug(f'found image with mode "{img.mode}" in {img_path}')
        pixel_array = np.array(img, dtype=np.uint16)  # Convert to 16-bit (DICOM standard)
        
        fileMeta = pydicom.Dataset()
        # fileMeta.MediaStorageSOPClassUID = pydicom._storage_sopclass_uids.SecondaryCaptureImageStorage 
        # ds.Modality = "OT"  # Other
        # TODO
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
                
        if per_instance_cb != None:
            per_instance_cb( i, ds )

        # Save the DICOM file
        #hash = await aiofiles_ext.async_hash_array(pixel_array)
        output_path = os.path.join(output_folder, f'{ds.SOPInstanceUID}.dcm')
        pydicom.dataset.validate_file_meta(ds.file_meta, enforce_standard=True)
        # ds.save_as(output_path, enforce_file_format=False)
        await async_save_as(ds, output_path, enforce_file_format=False)

    logging.debug(f"DICOM series created successfully in folder: {output_folder}")
    return output_folder