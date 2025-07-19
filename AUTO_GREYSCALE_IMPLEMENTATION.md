# Auto-Greyscale Implementation Summary - Updated for CBZ Support

## Files Updated/Created

### ✅ Updated Files:
1. **cli.py** - Added debug CLI arguments and debug handling functions (updated for CBZ support)
2. **conversion.py** - Already had auto-greyscale functionality
3. **utils.py** - Already had auto-greyscale parameter logging
4. **presets.py** - Already supported auto-greyscale parameters
5. **default_presets.json** - Already included auto-greyscale settings
6. **debug_utils.py** - **ENHANCED** with CBZ/CBR archive support

### ✅ New Files Created:
1. **debug_utils.py** - Complete debugging toolkit for auto-greyscale (now supports CBZ files)
2. **verify_auto_greyscale.py** - Verification script to test functionality

## Features Implemented

### 🎯 Core Auto-Greyscale Functionality:
- ✅ Automatic detection of near-greyscale images
- ✅ Pixel-level RGB difference analysis
- ✅ Configurable thresholds (pixel & percentage)
- ✅ Integration with existing conversion pipeline
- ✅ Preset support with auto-greyscale enabled by default for manga/comic
- ✅ **NEW: CBZ/CBR archive support in debug tools**

### 🔧 Debug Tools (Now with CBZ Support):
- ✅ **Single file analysis** (`--debug-auto-greyscale-single FILE_PATH`) - **NOW SUPPORTS CBZ/CBR FILES**
- ✅ Threshold testing (`--debug-test-thresholds IMAGE_PATH`) 
- ✅ **Directory analysis** (`--debug-analyze-directory DIRECTORY`) - **NOW SUPPORTS MIXED DIRECTORIES WITH CBZ AND IMAGES**
- ✅ Visual heatmaps and histograms (requires matplotlib)
- ✅ JSON analysis files
- ✅ Detailed statistics and recommendations
- ✅ **Archive-specific analysis with per-image breakdown**

### 📊 CLI Arguments Added:
```bash
# Auto-greyscale control
--auto-greyscale                    # Enable auto-detection
--auto-greyscale-pixel-threshold    # RGB difference threshold (default: 16)
--auto-greyscale-percent-threshold  # Colored pixel percentage (default: 0.01)

# Debug options (UPDATED)
--debug-auto-greyscale              # Enable debug during conversion
--debug-auto-greyscale-single FILE_PATH  # Analyze single IMAGE OR CBZ file and exit
--debug-test-thresholds IMAGE_PATH  # Test threshold ranges on image
--debug-analyze-directory DIR_PATH  # Batch analyze directory (images + CBZ files)
--debug-output-dir DIR_PATH         # Where to save debug files
```

### 🎨 Preset Integration:
- **manga**: Aggressive auto-greyscale (pixel_threshold=12, percent=0.005)
- **comic**: Standard auto-greyscale (pixel_threshold=16, percent=0.01) 
- **maximum_compression**: Aggressive auto-greyscale for maximum savings
- **photo/maximum_quality**: Auto-greyscale disabled for quality retention

## Usage Examples

### Basic conversion with auto-greyscale:
```bash
cbxtools input.cbz output/ --preset manga
cbxtools input.cbz output/ --auto-greyscale
```

### Debug CBZ file (NEW!):
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

### Analyze directory with mixed content (NEW!):
```bash
# This will now analyze both images AND CBZ files in the directory
cbxtools --debug-analyze-directory manga_collection/
```

### Custom thresholds:
```bash
cbxtools input.cbz output/ --auto-greyscale \
  --auto-greyscale-pixel-threshold 20 \
  --auto-greyscale-percent-threshold 0.02
```

## NEW CBZ Debug Features

### 🗂️ Archive Analysis:
- **Extracts and analyzes** all images in CBZ/CBR files
- **Per-image breakdown** with individual analysis files
- **Archive summary** showing conversion statistics
- **Visual heatmaps** for each image in the archive
- **Batch statistics** across all images in the archive

### 📈 Enhanced Directory Analysis:
- **Mixed content support** - analyze directories containing both images and CBZ files
- **Archive statistics** - shows conversion ratios for each CBZ file
- **Combined reporting** - aggregates results across all files and archives

### 📁 Debug Output Structure:
```
debug_auto_greyscale/
├── single_images/
│   ├── image_analysis.json
│   ├── image_diff_heatmap.png
│   └── image_histogram.png
└── archive_name/
    ├── archive_analysis_summary.json
    ├── page_001_analysis.json
    ├── page_001_diff_heatmap.png
    ├── page_001_histogram.png
    ├── page_002_analysis.json
    └── ...
```

## Dependencies

### Required:
- ✅ numpy (for image analysis)
- ✅ PIL/Pillow (already required)
- ✅ patoolib (for CBR extraction, already required)

### Optional:
- matplotlib (for debug visualizations)

## Verification

Run the verification script to ensure everything is working:
```bash
cd "D:\Portable Apps\cbxtools"
python verify_auto_greyscale.py
```

## Next Steps

1. **Test the CBZ functionality** with sample comic files:
   ```bash
   cbxtools --debug-auto-greyscale-single sample.cbz
   ```

2. **Test directory analysis** with mixed content:
   ```bash
   cbxtools --debug-analyze-directory your_comics_folder/
   ```

3. **Install matplotlib** if you want debug visualizations:
   ```bash
   pip install matplotlib
   ```

4. **Use auto-greyscale in production** with the manga or comic presets:
   ```bash
   cbxtools input.cbz output/ --preset manga
   ```

The auto-greyscale functionality now fully supports CBZ/CBR files in addition to individual images, making it much more useful for comic processing workflows!
