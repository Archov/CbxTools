# CBXTools Preset System

## Overview

The CBXTools preset system allows you to save and reuse conversion settings for different types of content. The system uses a consolidated architecture with unified preset management through the `presets.py` module, ensuring consistent behavior across all components.

### Architecture Benefits

- **Centralized Management**: Single implementation handles all preset operations
- **Consistent Validation**: Unified parameter validation across all presets
- **Caching System**: Improved performance with preset caching
- **Error Handling**: Consistent error messages and graceful fallbacks
- **Extension Support**: Easy addition of new preset parameters

## Storage and Loading

All presets are stored in a single JSON file located at `~/.cbxtools/presets.json`. The system:

- **Automatically creates** the preset file with defaults if it doesn't exist
- **Loads presets** into memory cache for fast access
- **Validates preset data** when loading to ensure consistency
- **Provides fallbacks** if preset files are corrupted or missing

## Using Presets

To use a preset:

```bash
cbxtools input.cbz output/ --preset comic
```

You can override specific settings from the preset:

```bash
cbxtools input.cbz output/ --preset comic --quality 90
```

The consolidated preset system ensures consistent parameter application across all modes (batch, watch, debug).

## Built-in Presets

The system comes with several built-in presets optimized through the consolidated architecture:

- **default**: Balanced settings for most use cases, optimized through `FileSystemUtils`
- **comic**: Optimized for comic books with `ImageAnalyzer` auto-greyscale detection
- **photo**: Higher quality for photographic content with minimal auto-processing
- **maximum_compression**: Prioritizes file size reduction with aggressive auto-greyscale via `ImageAnalyzer`
- **maximum_quality**: Highest quality with optional lossless compression
- **manga**: Optimized for manga content with aggressive greyscale detection and e-reader sizing

## Managing Presets

### Listing Available Presets

```bash
cbxtools --list-presets
```

This uses the consolidated preset cache for fast listing.

### Creating a New Preset

You can save your current settings as a preset:

```bash
cbxtools input.cbz output/ --quality 85 --lossless --save-preset "my_high_quality"
```

The unified preset management:
- **Validates parameters** before saving
- **Updates the cache** immediately
- **Provides clear error messages** if saving fails
- **Supports overwrite protection** by default

### Importing Presets

You can import presets from a JSON file:

```bash
cbxtools --import-preset all_presets.json
```

The consolidated system:
- **Validates imported presets** before merging
- **Provides detailed import statistics**
- **Handles conflicts gracefully**
- **Updates the memory cache** automatically

### Overwriting Existing Presets

Use the `--overwrite-preset` flag to update existing presets:

```bash
cbxtools input.cbz output/ --quality 90 --save-preset "comic" --overwrite-preset
```

## Preset Format

Presets are stored in JSON format with enhanced validation. Here's an example:

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

#### Auto-Greyscale Detection (via ImageAnalyzer)
- **auto_greyscale**: Boolean to enable automatic near-greyscale detection and conversion
- **auto_greyscale_pixel_threshold**: RGB difference threshold for detecting colored pixels (default: 16)
- **auto_greyscale_percent_threshold**: Percentage threshold for colored pixels (default: 0.01)
- **preserve_auto_greyscale_png**: Boolean to preserve intermediate PNG files during auto-greyscale conversion for debugging

#### Metadata
- **description**: Optional description of the preset

## Auto-Greyscale Integration

The preset system is fully integrated with the consolidated `ImageAnalyzer` for auto-greyscale functionality:

### Consistent Analysis
- **Same algorithms** used across batch, watch, and debug modes
- **Unified parameter validation** ensures threshold values are reasonable
- **Consistent error handling** for invalid threshold combinations

### Performance Benefits
- **Optimized algorithms** in `ImageAnalyzer` provide faster analysis
- **Cached preset loading** reduces overhead in watch mode
- **Efficient memory usage** through consolidated utilities

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

**Debug-friendly (preserves intermediate files)**:
```json
{
  "auto_greyscale": true,
  "auto_greyscale_pixel_threshold": 16,
  "auto_greyscale_percent_threshold": 0.01,
  "preserve_auto_greyscale_png": true
}
```

## Preset Resolution Order

The consolidated preset system follows a clear resolution order:

1. **Command-line arguments** (highest priority)
2. **Preset parameters** (from cache)
3. **Default values** (from consolidated defaults, lowest priority)

This ensures:
- **Predictable behavior** across all usage modes
- **Consistent overrides** regardless of context
- **Performance optimization** through parameter caching

```bash
# Use manga preset but with higher quality
cbxtools input.cbz output/ --preset manga --quality 85

# Use comic preset but disable auto-greyscale
cbxtools input.cbz output/ --preset comic --no-auto-greyscale
```

## Advanced Features

### Watch Mode Integration

Presets work seamlessly with watch mode through the consolidated architecture:

```bash
# Watch mode with manga preset
cbxtools input_dir/ output_dir/ --watch --preset manga

# Override preset settings in watch mode
cbxtools input_dir/ output_dir/ --watch --preset comic --quality 90
```

### Debug Mode Compatibility

Presets are fully compatible with debug operations:

```bash
# Debug with manga preset thresholds
cbxtools --debug-analyze-directory comics/ --preset manga

# Custom debug thresholds
cbxtools --debug-auto-greyscale-single comic.cbz --preset manga --auto-greyscale-pixel-threshold 20
```

### Batch Processing Optimization

The consolidated preset system optimizes batch operations:
- **Single preset load** for entire batch
- **Cached parameters** reduce per-file overhead
- **Consistent processing** across all files in batch

## Best Practices

### Creating Effective Presets

1. **Test thoroughly** with sample content before saving
2. **Use descriptive names** that indicate content type or purpose
3. **Include descriptions** to document preset purposes
4. **Group related settings** logically

### Performance Optimization

1. **Use appropriate method values** (higher for maximum compression)
2. **Set reasonable size limits** for target devices
3. **Enable auto-greyscale** for content that benefits from it
4. **Use appropriate compression levels** for your storage needs

### Maintenance

1. **Regular backup** of `~/.cbxtools/presets.json`
2. **Test presets** after CBXTools updates
3. **Clean up unused presets** periodically
4. **Document custom presets** for team sharing

The consolidated preset system provides reliable, high-performance configuration management that scales from single-file operations to large batch processing while maintaining consistency across all CBXTools features.