from setuptools import setup, Extension
from Cython.Build import cythonize
import glob
import os

# Ruta a los archivos
path = r"C:\Users\Moy\Documents\Python\Algorithmic Trading\HFT\Classes"

# Buscar todos los archivos .py
files = [os.path.join(path, py) for py in glob.glob(os.path.join(path, "*.py"))]

# Configuración de compilación
extensions = [Extension(name=os.path.splitext(os.path.basename(file))[0], sources=[file]) for file in files]

setup(
    name='ATLAS',
    ext_modules=cythonize(extensions),
    compiler_directives={'language_level': "3"},    
)
