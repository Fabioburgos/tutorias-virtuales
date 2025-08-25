# src/file_manager.py

import os
import tempfile
import shutil
import atexit
from datetime import datetime
from typing import Dict, Optional
import streamlit as st

class TemporaryFileManager:
    """
    Gestor de archivos temporales optimizado para Cloud Run
    """
    
    def __init__(self):
        self.temp_dirs = []
        self.created_files = []
        # Registrar limpieza automática al salir
        atexit.register(self.cleanup_all)
    
    def create_temp_directory(self, prefix: str = "tutorias_") -> str:
        """
        Crear un directorio temporal único
        
        Args:
            prefix: Prefijo para el nombre del directorio
            
        Returns:
            str: Ruta al directorio temporal creado
        """
        try:
            temp_dir = tempfile.mkdtemp(prefix=f"{prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}_")
            self.temp_dirs.append(temp_dir)
            return temp_dir
        except Exception as e:
            st.error(f"Error creando directorio temporal: {str(e)}")
            return None
    
    def create_temp_file(self, content: bytes, filename: str, directory: str = None) -> str:
        """
        Crear un archivo temporal con contenido específico
        
        Args:
            content: Contenido del archivo en bytes
            filename: Nombre del archivo
            directory: Directorio donde crear el archivo (opcional)
            
        Returns:
            str: Ruta al archivo temporal creado
        """
        try:
            if directory is None:
                directory = self.create_temp_directory()
            
            file_path = os.path.join(directory, filename)
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            self.created_files.append(file_path)
            return file_path
            
        except Exception as e:
            st.error(f"Error creando archivo temporal: {str(e)}")
            return None
    
    def get_temp_path(self, filename: str, directory: str = None) -> str:
        """
        Obtener ruta temporal para un archivo
        
        Args:
            filename: Nombre del archivo
            directory: Directorio específico (opcional)
            
        Returns:
            str: Ruta temporal para el archivo
        """
        if directory is None:
            directory = self.create_temp_directory()
        
        return os.path.join(directory, filename)
    
    def cleanup_directory(self, directory: str) -> bool:
        """
        Limpiar un directorio temporal específico
        
        Args:
            directory: Ruta del directorio a limpiar
            
        Returns:
            bool: True si se limpió exitosamente
        """
        try:
            if os.path.exists(directory):
                shutil.rmtree(directory)
                if directory in self.temp_dirs:
                    self.temp_dirs.remove(directory)
                return True
            return False
            
        except Exception as e:
            st.warning(f"Error limpiando directorio {directory}: {str(e)}")
            return False
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Eliminar un archivo específico
        
        Args:
            file_path: Ruta del archivo a eliminar
            
        Returns:
            bool: True si se eliminó exitosamente
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                if file_path in self.created_files:
                    self.created_files.remove(file_path)
                return True
            return False
            
        except Exception as e:
            st.warning(f"Error eliminando archivo {file_path}: {str(e)}")
            return False
    
    def cleanup_all(self) -> Dict[str, int]:
        """
        Limpiar todos los archivos y directorios temporales
        
        Returns:
            Dict: Estadísticas de limpieza
        """
        stats = {
            'directories_cleaned': 0,
            'files_cleaned': 0,
            'errors': 0
        }
        
        # Limpiar archivos individuales
        for file_path in self.created_files[:]:  # Copia para evitar modificación durante iteración
            if self.cleanup_file(file_path):
                stats['files_cleaned'] += 1
            else:
                stats['errors'] += 1
        
        # Limpiar directorios
        for directory in self.temp_dirs[:]:  # Copia para evitar modificación durante iteración
            if self.cleanup_directory(directory):
                stats['directories_cleaned'] += 1
            else:
                stats['errors'] += 1
        
        return stats
    
    def get_status(self) -> Dict:
        """
        Obtener estado actual del gestor de archivos
        
        Returns:
            Dict: Estado actual
        """
        return {
            'temp_directories': len(self.temp_dirs),
            'temp_files': len(self.created_files),
            'active_directories': [d for d in self.temp_dirs if os.path.exists(d)],
            'active_files': [f for f in self.created_files if os.path.exists(f)]
        }

class CloudRunFileManager(TemporaryFileManager):
    """
    Gestor especializado para Cloud Run con límites de memoria y espacio
    """
    
    def __init__(self, max_temp_size_mb: int = 100):
        super().__init__()
        self.max_temp_size_mb = max_temp_size_mb
        self.max_temp_size_bytes = max_temp_size_mb * 1024 * 1024
    
    def get_directory_size(self, directory: str) -> int:
        """
        Calcular el tamaño de un directorio en bytes
        
        Args:
            directory: Ruta del directorio
            
        Returns:
            int: Tamaño en bytes
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            st.warning(f"Error calculando tamaño del directorio: {str(e)}")
        
        return total_size
    
    def check_space_usage(self) -> Dict:
        """
        Verificar uso actual del espacio temporal
        
        Returns:
            Dict: Información del uso de espacio
        """
        total_size = 0
        directory_sizes = {}
        
        for directory in self.temp_dirs:
            if os.path.exists(directory):
                dir_size = self.get_directory_size(directory)
                directory_sizes[directory] = dir_size
                total_size += dir_size
        
        return {
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'max_size_mb': self.max_temp_size_mb,
            'usage_percentage': (total_size / self.max_temp_size_bytes) * 100,
            'directory_sizes': directory_sizes,
            'space_available': total_size < self.max_temp_size_bytes
        }
    
    def create_temp_directory(self, prefix: str = "tutorias_") -> str:
        """
        Crear directorio temporal con verificación de espacio
        """
        # Verificar espacio antes de crear
        space_info = self.check_space_usage()
        
        if not space_info['space_available']:
            st.warning(f"Espacio temporal lleno ({space_info['usage_percentage']:.1f}%). Limpiando archivos antiguos...")
            self.cleanup_oldest_files()
        
        return super().create_temp_directory(prefix)
    
    def cleanup_oldest_files(self) -> Dict[str, int]:
        """
        Limpiar archivos más antiguos para liberar espacio
        
        Returns:
            Dict: Estadísticas de limpieza
        """
        stats = {'directories_cleaned': 0, 'files_cleaned': 0, 'bytes_freed': 0}
        
        # Ordenar directorios por fecha de modificación
        directories_with_time = []
        for directory in self.temp_dirs:
            if os.path.exists(directory):
                mtime = os.path.getmtime(directory)
                size = self.get_directory_size(directory)
                directories_with_time.append((directory, mtime, size))
        
        # Ordenar por tiempo (más antiguos primero)
        directories_with_time.sort(key=lambda x: x[1])
        
        # Eliminar directorios más antiguos hasta liberar espacio suficiente
        for directory, mtime, size in directories_with_time:
            if self.cleanup_directory(directory):
                stats['directories_cleaned'] += 1
                stats['bytes_freed'] += size
                
            # Verificar si ya tenemos suficiente espacio
            space_info = self.check_space_usage()
            if space_info['space_available']:
                break
        
        return stats