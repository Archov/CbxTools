# Auto-Greyscale Implementation Summary - Refactored Architecture

## Architecture Overview

The auto-greyscale functionality has been fully refactored to use the new consolidated architecture:

- **Core Implementation**: `cbxtools.core.image_analyzer.ImageAnalyzer`
- **Debug Interface**: `debug_utils.py` (uses consolidated utilities)
- **Archive Support**: `cbxtools.core.archive_handler.ArchiveHandler`
- **Unified APIs**: Backward-compatible wrapper functions

## Refactored Components

### ✅ Core Utilities:
1. **`core/image_analyzer.py`** - Centralized image analysis algorithms
2. **`core/archive_handler.py`** - Unified archive extraction and creation
3. **`core/filesystem_utils.py`** - File operations and size calculations
4. **`debug_utils.py`** - Updated to use consolidated utilities

### ✅ Updated Files:
1. **`cli.py`** - Uses `PathValidator` and `FileSystemUtils`
2. **`conversion.py`** - Uses `ImageAnalyzer` for all image analysis
3. **`utils.py`** - Delegates to `FileSystemUtils`
4. **`watchers.py`** - Uses all consolidated utilities
5. **`near_greyscale_scan.py`** - Uses `ArchiveHandler` and `ImageAnalyzer`

## Features Implemented

### 🎯 Core Auto-Greyscale Functionality:
- ✅ Automatic detection of near-greyscale images via `ImageAnalyzer`
- ✅ Pixel-level RGB difference analysis with detailed statistics
- ✅ Configurable thresholds (pixel & percentage)
- ✅ Integration with existing conversion pipeline
- ✅ Preset support with auto-greyscale enabled by default for manga/comic
- ✅ **Unified CBZ/CBR archive support across all tools**
- ✅ **Consistent error handling and logging**

### 🔧 Debug Tools (Consolidated Architecture):
- ✅ **Single file analysis** (`--debug-auto-greyscale-single FILE_PATH`)
  - Supports both images and CBZ/CBR files
  - Uses `ImageAnalyzer.should_convert_to_greyscale_detailed()`
- ✅ **Threshold testing** (`--debug-test-thresholds IMAGE_PATH`)
  - Tests multiple threshold combinations
  - Generates comprehensive analysis reports
- ✅ **Directory analysis** (`--debug-analyze-directory DIRECTORY`)
  - Supports mixed directories with images and archives
  - Uses `ArchiveHandler.find_archives()` and `ImageAnalyzer.find_image_files()`
- ✅ **Visual heatmaps and histograms** (requires matplotlib)
- ✅ **JSON analysis files** with detailed statistics
- ✅ **Archive-specific analysis** with per-image breakdown

### 📊 CLI Arguments (Unchanged):
```bash
# Auto-greyscale control
--auto-greyscale                    # Enable auto-detection
--auto-greyscale-pixel-threshold    # RGB difference threshold (default: 16)
--auto-greyscale-percent-threshold  # Colored pixel percentage (default: 0.01)

# Debug options
--debug-auto-greyscale              # Enable debug during conversion
--debug-auto-greyscale-single FILE_PATH  # Analyze single image or CBZ file
--debug-test-thresholds IMAGE_PATH  # Test threshold ranges on image
--debug-analyze-directory DIR_PATH  # Batch analyze directory
--debug-output-dir DIR_PATH         # Where to save debug files
```

## New Consolidated API

### Direct Core Usage (Recommended for new code):
```python
from cbxtools.core.image_analyzer import ImageAnalyzer
from cbxtools.core.archive_handler import ArchiveHandler

# Core image analysis
max_diff, mean_diff, colored_ratio = ImageAnalyzer.analyze_colorfulness(img_array)
decision = ImageAnalyzer.should_convert_to_greyscale(img_array, 16, 0.01)

# Detailed debug analysis
decision, analysis = ImageAnalyzer.should_convert_to_greyscale_detailed(img_array, 16, 0.01)

# Archive operations
ArchiveHandler.extract_archive(archive_path, extract_dir, logger)
archives = ArchiveHandler.find_archives(directory, recursive=True)
```

### Legacy Compatibility (Maintained):
```python
from cbxtools.conversion import analyze_image_colorfulness, should_convert_to_greyscale
from cbxtools.debug_utils import should_convert_to_greyscale_debug
from cbxtools.archives import extract_archive, find_comic_archives

# Legacy APIs still work through wrapper functions
max_diff, mean_diff, colored_ratio = analyze_image_colorfulness(img_array)
decision = should_convert_to_greyscale(img_array, 16, 0.01)
```

## Benefits of Refactoring

### 🚀 Improved Maintainability:
- **Single source of truth** for image analysis algorithms
- **Consistent behavior** across all modules and tools
- **Easier debugging** with centralized logging and error handling
- **Simplified testing** of core functionality

### 📈 Enhanced Functionality:
- **Unified archive handling** across all components
- **Consistent path validation** and error messages
- **Optimized file operations** through consolidated utilities
- **Better performance** with reduced code duplication

### 🔧 Developer Benefits:
- **Clear extension points** for new functionality
- **Modular testing** capabilities
- **Consistent API patterns** across all utilities
- **Reduced cognitive load** when working with the codebase

## Usage Examples

### Basic conversion with auto-greyscale:
```bash
cbxtools input.cbz output/ --preset manga
cbxtools input.cbz output/ --auto-greyscale
```

### Debug CBZ file:
```bash
cbxtools --debug-auto-greyscale-single test_comic.cbz
```

### Debug single image:
```bash
cbxtools --debug-auto-greyscale-single test_image.jpg
```

### Test different thresholds:
```bash
cbxtools --debug-test-thresholds problem_image.jpg
```

### Analyze directory with mixed content:
```bash
# Analyzes both images AND CBZ files using consolidated utilities
cbxtools --debug-analyze-directory manga_collection/
```

### Custom thresholds:
```bash
cbxtools input.cbz output/ --auto-greyscale \
  --auto-greyscale-pixel-threshold 20 \
  --auto-greyscale-percent-threshold 0.02
```

## Debug Output Structure (Enhanced):
```
debug_auto_greyscale/
├── single_images/
│   ├── image_analysis.json           # Detailed analysis via ImageAnalyzer
│   ├── image_diff_heatmap.png        # Visual analysis
│   └── image_histogram.png           # Color distribution
└── archive_name/
    ├── archive_analysis_summary.json # Archive-wide statistics
    ├── page_001_analysis.json        # Per-page analysis
    ├── page_001_diff_heatmap.png     # Per-page visualization
    └── ...                           # Additional pages
```

## Dependencies

### Required:
- ✅ numpy (for image analysis in `ImageAnalyzer`)
- ✅ PIL/Pillow (for image processing)
- ✅ patoolib (for CBR extraction via `ArchiveHandler`)
- ✅ py7zr (for CB7 extraction via `ArchiveHandler`)

### Optional:
- matplotlib (for debug visualizations)

## Migration Guide

### For Existing Code:
1. **Direct usage** - Replace imports to use core utilities
2. **Legacy compatibility** - Existing code continues to work
3. **Gradual migration** - Update modules one at a time

### For New Development:
1. **Use core utilities directly** for new features
2. **Follow established patterns** in consolidated modules
3. **Extend base classes** for new functionality

## Testing

Run the verification script to ensure functionality:
```bash
cd "D:\Portable Apps\cbxtools"
python test_refactoring.py
```

## Next Steps

1. **Test consolidated functionality** with sample files:
   ```bash
   cbxtools --debug-auto-greyscale-single sample.cbz
   ```

2. **Verify directory analysis** works with refactored utilities:
   ```bash
   cbxtools --debug-analyze-directory your_comics_folder/
   ```

3. **Performance testing** to verify optimization benefits

4. **Integration testing** to ensure all components work together

The auto-greyscale functionality now benefits from the consolidated architecture while maintaining full backward compatibility and enhanced debugging capabilities!
