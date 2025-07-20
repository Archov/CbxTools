#!/usr/bin/env python3
"""
Preset management for CBZ/CBR to WebP converter.
Loads default presets from JSON file and manages user presets.
"""

import json
import os
from pathlib import Path
import logging

# Default location for preset file
DEFAULT_CONFIG_DIR = Path.home() / '.cbxtools'
DEFAULT_PRESET_FILE = DEFAULT_CONFIG_DIR / 'presets.json'

# Global cache of loaded presets
_PRESETS_CACHE = None

def get_default_presets_path():
    """Get the path to the default presets JSON file."""
    # Try to find default_presets.json in the same directory as this module
    current_dir = Path(__file__).parent
    default_presets_path = current_dir / 'default_presets.json'
    
    if default_presets_path.exists():
        return default_presets_path
    
    # Fallback: check if it's in the package data
    try:
        import pkg_resources
        return Path(pkg_resources.resource_filename('cbxtools', 'default_presets.json'))
    except (ImportError, FileNotFoundError):
        pass
    
    # Last resort: return None, we'll use minimal defaults
    return None

def load_default_presets():
    """Load default presets from JSON file."""
    default_path = get_default_presets_path()
    
    if default_path and default_path.exists():
        try:
            with open(default_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not load default presets from {default_path}: {e}")
    
    # Minimal fallback if we can't load the JSON file
    return {
        "default": {
            "quality": 80,
            "method": 4,
            "preprocessing": None,
            "zip_compression": 6,
            "auto_greyscale": False,
            "auto_greyscale_pixel_threshold": 16,
            "auto_greyscale_percent_threshold": 0.01,
            "description": "Default settings with balanced quality and performance"
        }
    }

def ensure_preset_file():
    """Ensure the preset file exists and is initialized with defaults if needed."""
    global _PRESETS_CACHE
    
    # Create config directory if it doesn't exist
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # If preset file doesn't exist, create it with default presets
    if not DEFAULT_PRESET_FILE.exists():
        default_presets = load_default_presets()
        with open(DEFAULT_PRESET_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_presets, f, indent=2)
        _PRESETS_CACHE = default_presets.copy()
        return DEFAULT_PRESET_FILE
    
    # Load existing presets if not already cached
    if _PRESETS_CACHE is None:
        try:
            with open(DEFAULT_PRESET_FILE, 'r', encoding='utf-8') as f:
                _PRESETS_CACHE = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # If there's an error with the file, use defaults and don't overwrite
            _PRESETS_CACHE = load_default_presets()
    
    return DEFAULT_PRESET_FILE

def list_available_presets():
    """List all available presets from the cache."""
    ensure_preset_file()  # Make sure cache is loaded
    return sorted(_PRESETS_CACHE.keys())

def save_preset(name, parameters, overwrite=False, logger=None):
    """
    Save a preset by appending/updating it in the presets.json file.
    
    Args:
        name: Name of the preset
        parameters: Dictionary of preset parameters
        overwrite: Whether to overwrite existing preset with same name
        logger: Optional logger for messages
    
    Returns:
        True if saved successfully, False otherwise
    """
    global _PRESETS_CACHE
    
    # Ensure file exists and cache is loaded
    ensure_preset_file()
    
    # Check if preset already exists and overwrite is not allowed
    if name in _PRESETS_CACHE and not overwrite:
        if logger:
            logger.error(f"Preset '{name}' already exists. Use --overwrite-preset to replace it.")
        return False
    
    try:
        # Update cache
        _PRESETS_CACHE[name] = parameters
        
        # Write updated cache to file
        with open(DEFAULT_PRESET_FILE, 'w', encoding='utf-8') as f:
            json.dump(_PRESETS_CACHE, f, indent=2)
            
        if logger:
            if overwrite and name in _PRESETS_CACHE:
                logger.info(f"Updated preset '{name}'")
            else:
                logger.info(f"Saved new preset '{name}'")
                
        return True
        
    except (IOError, OSError) as e:
        if logger:
            logger.error(f"Error saving preset: {e}")
        return False

def import_presets_from_file(file_path, overwrite=False, logger=None):
    """
    Import presets from a JSON file and merge with existing presets.
    
    Args:
        file_path: Path to the JSON file to import
        overwrite: Whether to overwrite existing presets
        logger: Optional logger for messages
    
    Returns:
        Number of imported presets, or -1 if error
    """
    global _PRESETS_CACHE
    
    # Ensure our preset file exists and cache is loaded
    ensure_preset_file()
    
    try:
        # Load presets from the file
        with open(file_path, 'r', encoding='utf-8') as f:
            imported_presets = json.load(f)
            
        if not isinstance(imported_presets, dict):
            if logger:
                logger.error(f"Invalid preset file format: {file_path}")
            return -1
            
        # Count how many presets we'll import
        import_count = 0
        
        # Merge with existing presets
        for name, preset in imported_presets.items():
            if name not in _PRESETS_CACHE or overwrite:
                _PRESETS_CACHE[name] = preset
                import_count += 1
                
        # Save merged presets
        with open(DEFAULT_PRESET_FILE, 'w', encoding='utf-8') as f:
            json.dump(_PRESETS_CACHE, f, indent=2)
            
        if logger:
            logger.info(f"Imported {import_count} presets from {file_path}")
            
        return import_count
        
    except (json.JSONDecodeError, IOError) as e:
        if logger:
            logger.error(f"Error importing presets: {e}")
        return -1

def get_preset_parameters(preset_name, logger=None):
    """
    Get parameters for the specified preset from the cache.
    
    Args:
        preset_name: Name of the preset to load
        logger: Optional logger for messages
    
    Returns:
        Dictionary of preset parameters, or empty dict if preset not found
    """
    # Ensure file exists and cache is loaded
    ensure_preset_file()
    
    # Check if preset exists in cache
    if preset_name in _PRESETS_CACHE:
        if logger:
            logger.debug(f"Using preset: {preset_name}")
        return _PRESETS_CACHE[preset_name]
    
    # Handle preset not found
    if logger:
        logger.warning(f"Preset '{preset_name}' not found, using default settings")
    
    # Return default preset or empty dict if default doesn't exist
    return _PRESETS_CACHE.get("default", {})

def apply_preset_with_overrides(preset_name, overrides, logger=None):
    """
    Apply a preset and override specific parameters.
    
    Args:
        preset_name: Name of the preset to load
        overrides: Dictionary of parameters to override from the preset
        logger: Optional logger for messages
    
    Returns:
        Dictionary of final parameters with defaults applied
    """
    # Get the base preset parameters
    params = get_preset_parameters(preset_name, logger)
    
    # Apply overrides for any non-None values
    for key, value in overrides.items():
        if value is not None:
            params[key] = value
    
    # Apply defaults for essential parameters if missing
    defaults = {
        'quality': 80,
        'max_width': 0,
        'max_height': 0,
        'method': 4,
        'preprocessing': None,
        'zip_compression': 6,
        'lossless': False,
        'grayscale': False,
        'auto_contrast': False,
        'auto_greyscale': False,
        'auto_greyscale_pixel_threshold': 16,
        'auto_greyscale_percent_threshold': 0.01
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    return params

def export_preset_from_args(args):
    """
    Export a preset from command-line arguments.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Dictionary of parameters extracted from args
    """
    # Extract relevant parameters from args
    params = {}
    possible_params = [
        'quality', 'max_width', 'max_height', 'method',
        'preprocessing', 'zip_compression', 'lossless',
        'grayscale', 'auto_contrast',
        'auto_greyscale', 'auto_greyscale_pixel_threshold', 'auto_greyscale_percent_threshold'
    ]
    
    for param in possible_params:
        if hasattr(args, param):
            value = getattr(args, param)
            if value is not None:  # Only include non-None values
                params[param] = value
    
    return params

# Load presets on module import
_ = ensure_preset_file()