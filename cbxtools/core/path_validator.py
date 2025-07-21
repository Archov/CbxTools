#!/usr/bin/env python3
"""
Centralized path validation and resolution utilities.
"""

from pathlib import Path


class PathValidator:
    """Utilities for path validation and resolution."""
    
    @staticmethod
    def validate_input_path(input_path_str, must_exist=True):
        """
        Validate and resolve input path.
        
        Args:
            input_path_str: Input path string
            must_exist: Whether path must exist
            
        Returns:
            Path: Resolved input path
            
        Raises:
            ValueError: If path is invalid or doesn't exist when required
        """
        if not input_path_str:
            raise ValueError("Input path cannot be empty")
        
        input_path = Path(input_path_str).resolve()
        
        if must_exist and not input_path.exists():
            raise ValueError(f"Input path not found: {input_path}")
        
        return input_path
    
    @staticmethod
    def validate_output_path(output_path_str, create_if_missing=True):
        """
        Validate and resolve output path.
        
        Args:
            output_path_str: Output path string
            create_if_missing: Whether to create directory if it doesn't exist
            
        Returns:
            Path: Resolved output path
            
        Raises:
            ValueError: If path is invalid
        """
        if not output_path_str:
            raise ValueError("Output path cannot be empty")
        
        output_path = Path(output_path_str).resolve()
        
        if create_if_missing:
            output_path.mkdir(parents=True, exist_ok=True)
        
        return output_path
    
    @staticmethod
    def validate_file_path(file_path_str, must_exist=True, extensions=None):
        """
        Validate a file path with optional extension checking.
        
        Args:
            file_path_str: File path string
            must_exist: Whether file must exist
            extensions: Set of allowed extensions (with dots)
            
        Returns:
            Path: Resolved file path
            
        Raises:
            ValueError: If file is invalid or has wrong extension
        """
        if not file_path_str:
            raise ValueError("File path cannot be empty")
        
        file_path = Path(file_path_str).resolve()
        
        if must_exist and not file_path.exists():
            raise ValueError(f"File not found: {file_path}")
        
        if must_exist and not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        if extensions and file_path.suffix.lower() not in extensions:
            raise ValueError(f"File must have one of these extensions: {extensions}")
        
        return file_path
    
    @staticmethod
    def validate_directory_path(dir_path_str, must_exist=True, create_if_missing=False):
        """
        Validate a directory path.
        
        Args:
            dir_path_str: Directory path string
            must_exist: Whether directory must exist
            create_if_missing: Whether to create directory if missing
            
        Returns:
            Path: Resolved directory path
            
        Raises:
            ValueError: If directory is invalid
        """
        if not dir_path_str:
            raise ValueError("Directory path cannot be empty")
        
        dir_path = Path(dir_path_str).resolve()
        
        if not dir_path.exists():
            if must_exist and not create_if_missing:
                raise ValueError(f"Directory not found: {dir_path}")
            elif create_if_missing:
                dir_path.mkdir(parents=True, exist_ok=True)
        elif dir_path.exists() and not dir_path.is_dir():
            raise ValueError(f"Path is not a directory: {dir_path}")
        
        return dir_path
    
    @staticmethod
    def resolve_relative_output_path(input_path, output_base_dir, preserve_structure=True):
        """
        Resolve output path maintaining directory structure.
        
        Args:
            input_path: Input file/directory path
            output_base_dir: Base output directory
            preserve_structure: Whether to preserve directory structure
            
        Returns:
            Path: Resolved output path
        """
        input_path = Path(input_path)
        output_base_dir = Path(output_base_dir)
        
        if preserve_structure and input_path.parent != input_path.parent.anchor:
            # Preserve relative directory structure
            rel_path = input_path.parent.relative_to(input_path.parent.parent)
            output_dir = output_base_dir / rel_path
        else:
            # Direct output to base directory
            output_dir = output_base_dir
        
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
