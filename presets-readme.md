# CBXTools Preset System

## Overview

The CBXTools preset system allows you to save and reuse conversion settings for different types of content. All presets are stored in a single JSON file located at `~/.cbxtools/presets.json`. This file is automatically loaded when you use the tool, and new presets are added to this file when you save them.

## Using Presets

To use a preset:

```bash
cbxtools input.cbz output/ --preset comic
```

You can override specific settings from the preset:

```bash
cbxtools input.cbz output/ --preset comic --quality 90
```

## Built-in Presets

The system comes with several built-in presets:

- **default**: Balanced settings for most use cases
- **comic**: Optimized for comic books with line art and text, includes auto-greyscale detection
- **photo**: Higher quality for photographic content
- **maximum_compression**: Prioritizes file size reduction with aggressive auto-greyscale
- **maximum_quality**: Highest quality with optional lossless compression
- **manga**: Optimized for manga content with aggressive greyscale detection and e-reader sizing

## Managing Presets

### Listing Available Presets

```bash
cbxtools --list-presets
```

### Creating a New Preset

You can save your current settings as a preset:

```bash
cbxtools input.cbz output/ --quality 85 --lossless --save-preset "my_high_quality"
```

This will add the preset to the `presets.json` file.

### Importing Presets

You can import presets from a JSON file:

```bash
cbxtools --import-preset all_presets.json
```

The imported presets will be merged with existing presets in your `presets.json` file.

### Overwriting Existing Presets

Use the `--overwrite-preset` flag to update existing presets:

```bash
cbxtools input.cbz output/ --quality 90 --save-preset "comic" --overwrite-preset
```

## Preset Format

Presets are stored in JSON format. Here's an example:

```json
{
  "manga": {
    "quality": 70,
    "method": 6,
    "preprocessing": null,
    "zip_compression": 9,
    "max_width": 0,
    "max_height": 2400,
    "lossless": false,
    "auto_greyscale": true,
    "auto_greyscale_pixel_threshold": 16,
    "auto_greyscale_percent_threshold": 0.01,
    "preserve_auto_greyscale_png": false,
    "description": "Optimized for manga with aggressive greyscale detection and size limits for e-readers"
  }
}
```

### Available Parameters

#### Basic Quality Settings
- **quality**: WebP compression quality (0-100)
- **method**: WebP compression method (0-6, higher = better compression but slower)
- **lossless**: Boolean to enable lossless compression

#### Size and Preprocessing
- **max_width**: Maximum width in pixels (0 = no limit)
- **max_height**: Maximum height in pixels (0 = no limit)
- **preprocessing**: One of "none", "unsharp_mask", "reduce_noise", or null

#### Archive Settings
- **zip_compression**: ZIP compression level for CBZ files (0-9)

#### Image Transformation
- **grayscale**: Boolean to force grayscale conversion
- **auto_contrast**: Boolean to enable automatic contrast enhancement

#### Auto-Greyscale Detection
- **auto_greyscale**: Boolean to enable automatic near-greyscale detection and conversion
- **auto_greyscale_pixel_threshold**: RGB difference threshold for detecting colored pixels (default: 16)
- **auto_greyscale_percent_threshold**: Percentage threshold for colored pixels (default: 0.01)
- **preserve_auto_greyscale_png**: Boolean to preserve intermediate PNG files during auto-greyscale conversion for debugging

#### Metadata
- **description**: Optional description of the preset

## Auto-Greyscale Preset Configuration

The auto-greyscale parameters are particularly important for manga and comic presets:

- **Lower pixel_threshold** (e.g., 12-16): More sensitive to color differences, catches subtle coloring
- **Higher pixel_threshold** (e.g., 20-24): Less sensitive, only converts clearly near-greyscale images
- **Lower percent_threshold** (e.g., 0.005): Converts more images to greyscale
- **Higher percent_threshold** (e.g., 0.02): Only converts images with very few colored pixels

### Example Auto-Greyscale Configurations

**Aggressive (manga preset)**:
```json
{
  "auto_greyscale": true,
  "auto_greyscale_pixel_threshold": 16,
  "auto_greyscale_percent_threshold": 0.01
}
```

**Conservative (for mixed content)**:
```json
{
  "auto_greyscale": true,
  "auto_greyscale_pixel_threshold": 20,
  "auto_greyscale_percent_threshold": 0.02
}
```

**Debug-friendly**:
```json
{
  "auto_greyscale": true,
  "auto_greyscale_pixel_threshold": 16,
  "auto_greyscale_percent_threshold": 0.01,
  "preserve_auto_greyscale_png": true
}
```

## Preset Resolution Order

When determining what settings to use, the system follows this order:

1. Command-line arguments (highest priority)
2. Preset parameters
3. Default values (lowest priority)

This means you can always override preset settings with command-line options:

```bash
# Use manga preset but with higher quality
cbxtools input.cbz output/ --preset manga --quality 85

# Use comic preset but disable auto-greyscale
cbxtools input.cbz output/ --preset comic --no-auto-greyscale
```