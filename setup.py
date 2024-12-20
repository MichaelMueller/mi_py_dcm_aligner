from setuptools import setup, find_packages
from mi_py_dcm_aligner.app import App

def parse_requirements():
    with open("requirements.txt", "r") as file:
        return [line.strip() for line in file if line and not line.startswith('#')]
    
def parse_description_from_readme() -> str:
    with open("README.md", "r") as file:
        return file.read().splitlines()[1]

setup(
    name=App.TITLE,               # Replace with your package's name
    version=App.VERSION,
    packages=find_packages(),        # Automatically find sub
    install_requires=parse_requirements(),
    author='Michael Mueller',
    author_email='michaelmuelleronline@gmx.de',
    description=parse_description_from_readme(),
    url='https://github.com/MichaelMueller/mi_py_dicom_object_alignment.git',  # Link to your repository
)
