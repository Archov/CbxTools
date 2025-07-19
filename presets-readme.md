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
- **comic**: Optimized for comic books with line art and text
- **photo**: Higher quality for photographic content
- **maximum_compression**: Prioritizes file size reduction
- **maximum_quality**: Highest quality with optional lossless compression
- **manga**: Optimized for manga content with aggressive greyscale detection

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
    "quality": 75,
    "method": 6,
    "preprocessing": "unsharp_mask",
    "zip_compression": 9,
    "max_width": 1400,
    "max_height": 2000,
    "lossless": false,
    "description": "Optimized for manga with text enhancement and size limits"
  }
}
```

### Available Parameters

- **quality**: WebP compression quality (0-100)
- **method**: WebP compression method (0-6, higher = better compression but slower)
- **preprocessing**: One of "none", "unsharp_mask", "reduce_noise"
- **zip_compression**: ZIP compression level for CBZ files (0-9)
- **max_width**: Maximum width in pixels (0 = no limit)
- **max_height**: Maximum height in pixels (0 = no limit)
- **lossless**: Boolean to enable lossless compression
- **description**: Optional description of the preset

## Preset Resolution Order

When determining what settings to use, the system follows this order:

1. Command-line arguments
2. Preset parameters
3. Default values