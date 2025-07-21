#!/usr/bin/env python3
"""
Unified image analysis utilities for auto-greyscale detection.
Consolidates analysis logic with optional debug information.
"""

import numpy as np
from PIL import Image
from pathlib import Path
import os


class ImageAnalyzer:
    """Centralized image analysis for auto-greyscale detection."""
    
    @staticmethod
    def analyze_colorfulness(img_array, pixel_threshold=16):
        """
        Analyze if an image is effectively greyscale by checking pixel color variation.
        
        Args:
            img_array: numpy array of image data (RGB)
            pixel_threshold: threshold for considering a pixel "colored"
        
        Returns:
            tuple: (max_diff, mean_diff, colored_ratio)
        """
        # Calculate per-pixel difference between max and min RGB values
        diffs = img_array.max(axis=2).astype(int) - img_array.min(axis=2).astype(int)
        max_diff = int(diffs.max())
        mean_diff = float(diffs.mean())
        colored_pixels = int(np.count_nonzero(diffs > pixel_threshold))
        total_pixels = diffs.size
        colored_ratio = colored_pixels / total_pixels
        
        return max_diff, mean_diff, colored_ratio
    
    @classmethod
    def analyze_colorfulness_detailed(cls, img_array, pixel_threshold=16):
        """
        Extended analysis with additional debug statistics.
        
        Args:
            img_array: numpy array of image data (RGB)
            pixel_threshold: threshold for considering a pixel "colored"
        
        Returns:
            dict: Extended debug information including all statistics
        """
        # Get core analysis
        max_diff, mean_diff, colored_ratio = cls.analyze_colorfulness(img_array, pixel_threshold)
        
        # Add extended debug statistics
        diffs = img_array.max(axis=2).astype(int) - img_array.min(axis=2).astype(int)
        std_diff = float(diffs.std())
        median_diff = float(np.median(diffs))
        percentile_95 = float(np.percentile(diffs, 95))
        percentile_99 = float(np.percentile(diffs, 99))
        
        # Count pixels in different ranges
        colored_pixels = int(np.count_nonzero(diffs > pixel_threshold))
        very_colored = int(np.count_nonzero(diffs > pixel_threshold * 2))
        slightly_colored = int(np.count_nonzero((diffs > pixel_threshold) & (diffs <= pixel_threshold * 2)))
        total_pixels = diffs.size
        
        return {
            'max_diff': max_diff,
            'mean_diff': mean_diff,
            'std_diff': std_diff,
            'median_diff': median_diff,
            'percentile_95': percentile_95,
            'percentile_99': percentile_99,
            'colored_pixels': colored_pixels,
            'very_colored_pixels': very_colored,
            'slightly_colored_pixels': slightly_colored,
            'total_pixels': total_pixels,
            'colored_ratio': colored_ratio,
            'very_colored_ratio': very_colored / total_pixels,
            'slightly_colored_ratio': slightly_colored / total_pixels,
            'pixel_threshold_used': pixel_threshold,
            'image_shape': img_array.shape
        }
    
    @classmethod
    def should_convert_to_greyscale(cls, img_array, pixel_threshold=16, percent_threshold=0.01):
        """
        Determine if an image should be converted to greyscale.
        
        Args:
            img_array: numpy array of image data (RGB)
            pixel_threshold: per-pixel difference threshold for "colored" pixels
            percent_threshold: fraction of colored pixels above which image is considered colorful
        
        Returns:
            bool: True if image should be converted to greyscale
        """
        max_diff, _, colored_ratio = cls.analyze_colorfulness(img_array, pixel_threshold)
        # Don't convert if there are no colored pixels (already effectively greyscale)
        if colored_ratio == 0.0:
            return False
        return colored_ratio <= percent_threshold
    
    @classmethod
    def should_convert_to_greyscale_detailed(cls, img_array, pixel_threshold=16, percent_threshold=0.01):
        """
        Determine if image should be converted to greyscale with detailed analysis.
        
        Returns:
            tuple: (decision, debug_info)
        """
        # Use the main conversion function for the decision
        decision = cls.should_convert_to_greyscale(img_array, pixel_threshold, percent_threshold)
        
        # Get extended debug information
        analysis = cls.analyze_colorfulness_detailed(img_array, pixel_threshold)
        
        # Add decision information
        analysis['decision'] = decision
        analysis['percent_threshold_used'] = percent_threshold
        
        # Generate decision reason based on the actual logic
        if analysis['colored_pixels'] == 0:
            analysis['decision_reason'] = "colored_pixels is 0 (already effectively greyscale)"
        else:
            analysis['decision_reason'] = f"colored_ratio ({analysis['colored_ratio']:.4f}) {'<=' if decision else '>'} percent_threshold ({percent_threshold})"
        
        return decision, analysis
    
    @staticmethod
    def convert_to_bw_with_contrast(img):
        """Convert image to black and white with auto contrast enhancement."""
        from PIL import ImageOps
        
        # First convert to black and white (grayscale)
        bw_img = img.convert('L')
        
        # Then apply auto contrast to the black and white image
        enhanced_bw_img = ImageOps.autocontrast(bw_img)
        
        return enhanced_bw_img
    
    @staticmethod
    def is_image_file(file_path):
        """Check if a file is an image based on its extension."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.tga', '.ico'}
        return Path(file_path).suffix.lower() in image_extensions
    
    @classmethod
    def find_image_files(cls, directory, recursive=False):
        """Find all image files in the given directory."""
        from pathlib import Path
        import os
        
        images = []

        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = Path(root) / file
                    if cls.is_image_file(file_path):
                        images.append(file_path)
        else:
            for file in os.listdir(directory):
                file_path = Path(directory) / file
                if file_path.is_file() and cls.is_image_file(file_path):
                    images.append(file_path)

        return sorted(images)
