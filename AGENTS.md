# CBXTools Codebase Overview

## Project Description
CBXTools is a comprehensive comic book archive converter that transforms CBZ/CBR/CB7 files to WebP format while preserving quality and reducing file sizes. The tool focuses on intelligent compression with automatic greyscale detection, metadata preservation, and batch processing capabilities.

## Repository Structure

```
cbxtools/
├── cbxtools/                    # Main package directory
│   ├── __init__.py             # Package initialization
│   ├── __main__.py             # Entry point for module execution
│   ├── cli.py                  # Command-line interface and argument parsing
│   ├── conversion.py           # Wrapper around core image utilities
│   ├── debug_utils.py          # Debug helpers built on ImageAnalyzer
│   ├── archives.py             # Legacy archive helpers
│   ├── utils.py                # Compatibility utilities and logging setup
│   ├── presets.py              # Preset management system
│   ├── stats_tracker.py        # Statistics tracking and reporting
│   ├── watchers.py             # Watch mode functionality
│   ├── near_greyscale_scan.py  # Near-greyscale image detection
│   ├── default_presets.json    # Default preset configurations
│   └── core/                   # Consolidated implementation layer
│       ├── __init__.py
│       ├── archive_handler.py
│       ├── filesystem_utils.py
│       ├── image_analyzer.py
│       ├── packaging_worker.py
│       └── path_validator.py
├── setup.py                    # Package setup and dependencies
├── README.md                   # Main documentation
├── Legacy/                     # Legacy scripts
└── Documentation files         # Various .md files for features
```

## Core Components

### Code Architecture - Shared Functions

#### Critical: Single Source of Truth
The authoritative greyscale detection logic lives in
`cbxtools.core.image_analyzer.ImageAnalyzer`.
`conversion.py` re-exports helper functions for backward compatibility, while
`debug_utils.py`, `near_greyscale_scan.py` and other modules call into the
`ImageAnalyzer` class. **Never duplicate core logic**—delegate to these core
utilities so updates automatically propagate.

#### Function Relationships
- `debug_utils.py` provides `*_debug()` variants that call `ImageAnalyzer`
  for the core decision logic
- `conversion.py` wraps `ImageAnalyzer` methods for backward compatibility
- `near_greyscale_scan.py` and `archives.py` use `ArchiveHandler` and
  `ImageAnalyzer` from the `core` package
- Any changes to `cbxtools.core` automatically apply to all modules

### 1. CLI Interface (`cli.py`)
**Purpose**: Command-line argument parsing and application orchestration
**Key Functions**:
- `parse_arguments()`: Comprehensive argument parsing with preset support
- `main()`: Application entry point and workflow coordination
- `check_and_install_dependencies()`: Automatic dependency management
- `handle_*_operations()`: Specialized handlers for different operation modes

**Key Features**:
- Supports presets for common use cases (comic, manga, photo, etc.)
- Built-in dependency checking and installation
- Multiple operation modes (convert, watch, scan, debug)
- Comprehensive parameter validation

### 2. Image Conversion (`conversion.py`)
**Purpose**: Core image processing and WebP conversion
**Key Functions**:
- `convert_single_image()`: Individual image processing with auto-greyscale detection
- `convert_to_webp()`: Batch image conversion with metadata preservation
- `analyze_image_colorfulness()`: Color analysis for greyscale detection
- `should_convert_to_greyscale()`: Intelligent greyscale conversion decision
- `convert_to_bw_with_contrast()`: Enhanced B&W conversion with auto-contrast

**Key Features**:
- Multi-threaded parallel processing
- Automatic greyscale detection with configurable thresholds
- Advanced preprocessing options (unsharp mask, noise reduction)
- Quality-preserving resizing and format conversion
- Non-image file preservation for metadata

### 3. Archive Management (`archives.py`)
**Purpose**: Comic archive extraction and creation
**Key Functions**:
- `extract_archive()`: Supports CBZ/CBR/CB7 formats
- `create_cbz()`: Optimized CBZ creation with compression control
- `find_comic_archives()`: Recursive archive discovery
- `find_image_files()`: Image file discovery and validation

**Key Features**:
- Multi-format support (ZIP, RAR, 7Z)
- Optimized compression settings
- Recursive directory traversal
- File type validation

### 4. Preset System (`presets.py`)
**Purpose**: Configuration management and preset handling
**Key Functions**:
- `apply_preset_with_overrides()`: Intelligent preset application
- `save_preset()`: Custom preset creation and storage
- `import_presets_from_file()`: Bulk preset import
- `get_preset_parameters()`: Preset parameter retrieval

**Default Presets**:
- `default`: Balanced quality and performance
- `comic`: Optimized for line art with auto-greyscale
- `manga`: Aggressive greyscale detection for manga content
- `photo`: High-quality settings for photographic content
- `maximum_compression`: Size-focused with aggressive compression
- `maximum_quality`: Quality-focused with optional lossless

### 5. Statistics Tracking (`stats_tracker.py`)
**Purpose**: Performance monitoring and usage analytics
**Key Functions**:
- `StatsTracker`: Persistent statistics storage
- `print_summary_report()`: Detailed conversion reports
- `print_lifetime_stats()`: Historical usage statistics

**Tracked Metrics**:
- Files processed count
- Size reduction statistics
- Execution time tracking
- Run history maintenance

### 6. Watch Mode (`watchers.py`)
**Purpose**: Automated directory monitoring and processing
**Key Functions**:
- `watch_directory()`: Main watch loop with file monitoring
- `find_all_watchable_items()`: Multi-type file discovery
- `cleanup_empty_directories()`: Automated cleanup

**Features**:
- Real-time file system monitoring
- Recursive directory watching
- Automatic file deletion after processing
- Directory structure preservation
- Multi-threaded processing pipeline

### 7. Near-Greyscale Analysis (`near_greyscale_scan.py`)
**Purpose**: Bulk analysis of archives for greyscale content
**Key Functions**:
- `archive_contains_near_greyscale()`: Single archive analysis
- `scan_directory_for_near_greyscale()`: Bulk directory scanning

**Scan Modes**:
- `dryrun`: Generate list of near-greyscale archives
- `move`: Relocate identified archives
- `process`: Convert identified archives

### 8. Debug Utilities (`debug_utils.py`)
**Purpose**: Development and troubleshooting tools
**Key Functions**:
- `debug_single_file_greyscale()`: Individual file analysis
- `test_threshold_ranges()`: Threshold optimization
- `analyze_directory_for_auto_greyscale()`: Bulk analysis

## Algorithm Details

### Auto-Greyscale Detection Algorithm
The core greyscale detection uses pixel-level color analysis:

1. **Color Difference Calculation**: For each pixel, calculate `max(R,G,B) - min(R,G,B)`
2. **Threshold Application**: Count pixels with difference > `pixel_threshold` (default: 16)
3. **Percentage Check**: If colored pixels < `percent_threshold` (default: 0.01), convert to greyscale
4. **Enhanced Conversion**: Apply greyscale + auto-contrast for optimal B&W appearance

#### Auto-Greyscale Edge Cases

##### Zero Colored Pixels Rule
- Images with `colored_ratio == 0.0` are **NOT** converted (already effectively greyscale)
- This prevents unnecessary processing of already-greyscale images
- WebP files can be in RGB mode but have zero color content

##### Threshold Logic
```python
if colored_ratio == 0.0:
    return False  # Already greyscale
return colored_ratio <= percent_threshold
```

##### Debug Categories
1. **Convert to Greyscale**: `0 < colored_ratio <= threshold`
2. **Keep Color**: `colored_ratio > threshold` 
3. **Already Greyscale**: `colored_ratio == 0.0`
4. **Skipped**: Native grayscale mode ('L')

### Multi-threaded Processing Pipeline
1. **Extraction**: Archive extraction (single-threaded per archive)
2. **Conversion**: Image processing (multi-threaded pool)
3. **Packaging**: CBZ creation (dedicated thread with queue)
4. **Statistics**: Async result collection and reporting

## Image Processing Pipelines

### Auto-Greyscale Workflow
1. Load image → RGB mode
2. Analyze color content → decision
3. If convert: Apply `convert_to_bw_with_contrast()`
4. Save to temporary PNG → reload → convert to WebP
5. Optional: Preserve PNG with `--preserve-auto-greyscale-png`

### Manual B&W vs Auto-Greyscale
- **B&W.py**: JPG → grayscale+contrast → PNG (direct)
- **CBXtools**: JPG → analyze → grayscale+contrast → temp PNG → WebP
- **Same core processing** but different analysis timing

## Dependencies

### Required
- **Pillow**: Image processing and format conversion
- **rarfile**: RAR archive extraction
- **patool**: General archive handling

### Optional
- **numpy**: Enhanced auto-greyscale performance
- **matplotlib**: Debug visualization capabilities
- **py7zr**: 7z archive support

## Configuration System

### Preset Parameters
Each preset can configure:
- `quality`: WebP compression quality (0-100)
- `method`: WebP compression method (0-6)
- `max_width`/`max_height`: Size constraints
- `preprocessing`: Image enhancement options
- `zip_compression`: CBZ compression level
- `lossless`: Enable lossless WebP
- `auto_greyscale`: Enable automatic greyscale detection
- `auto_greyscale_pixel_threshold`: Pixel-level threshold
- `auto_greyscale_percent_threshold`: Image-level threshold

### User Configuration
- Presets stored in `~/.cbxtools/presets.json`
 - Statistics stored in `~/.cbxtools/.cbx-tools-stats.json`
- Watch mode history in output directory

### Debug Parameter Resolution
1. **Command-line args** (highest priority)
2. **Preset values** (if args not specified)
3. **Default values** (fallback)

### Preset Application
- Debug operations respect `--preset` parameter
- Only auto-greyscale thresholds are used by debug
- Other conversion parameters ignored in debug mode

### Parameter Flow
```
CLI args → apply_preset_with_overrides() → final parameters → debug functions
```

## Usage Patterns

### Basic Conversion
```bash
cbxtools input.cbz output_directory/
```

### Preset Usage
```bash
cbxtools comics/ output/ --preset manga --quality 85
```

### Watch Mode
```bash
cbxtools incoming/ output/ --watch --delete-originals
```

### Bulk Analysis
```bash
cbxtools --scan-near-greyscale dryrun manga_collection/
```

## Debug System Architecture

### Debug vs Production Consistency
- Debug uses same algorithms as production conversion
- Extended debug functions provide additional statistics
- Analysis files show exact decision logic used

### Debug Output Structure
```python
# Analysis files contain:
{
  "decision": bool,           # Conversion decision
  "colored_ratio": float,     # Percentage of colored pixels  
  "decision_reason": str,     # Human-readable explanation
  "max_diff": int,           # Maximum color difference found
  "colored_pixels": int      # Count of pixels above threshold
}
```

### Debug Commands
- `--debug-auto-greyscale-single`: Analyze single file/archive
- `--preserve-auto-greyscale-png`: Keep intermediate PNG files
- `--debug-analyze-directory`: Batch analysis with statistics

## Performance Characteristics

### Optimization Features
- Multi-threaded image conversion
- Pipelined archive processing
- Memory-efficient streaming
- Incremental statistics updates
- Smart directory structure preservation

### Typical Performance
- Image conversion: 4-8 threads optimal
- Archive processing: 1 thread + packaging thread
- Compression ratios: 30-70% size reduction typical
- Auto-greyscale hit rate: 10-40% for manga content

## Error Handling

### Graceful Degradation
- Individual file failures don't stop batch processing
- Missing dependencies are detected and installation offered
- Corrupted archives are skipped with logging
- Insufficient permissions handled gracefully

### Recovery Mechanisms
- Watch mode maintains processing history
- Partial conversions can be resumed
- Statistics survive application crashes
- Empty directory cleanup on restart

## Common Issues & Solutions

### "Already Greyscale" Images Still Converting
- **Symptom**: Images with 0.0000 colored_ratio showing "→ GREYSCALE"
- **Cause**: Using `max_diff == 0` instead of `colored_ratio == 0.0`
- **Fix**: Check `colored_ratio == 0.0` for zero-colored-pixels detection

### Debug vs Production Differences  
- **Symptom**: Debug shows different results than actual conversion
- **Cause**: Code duplication between modules
- **Fix**: Ensure debug imports from `conversion.py`

### Missing Images in Debug Counts
- **Symptom**: "Found X images" but "Analyzed Y images" where Y < X
- **Cause**: Native greyscale images (mode 'L') are skipped
- **Fix**: Track skipped images separately in summary

## Extension Points

### Adding New Formats
1. Extend `extract_archive()` in `archives.py`
2. Update `find_comic_archives()` file extension list
3. Add format-specific error handling

### Custom Preprocessing
1. Add new options to `preprocessing` parameter
2. Implement in `convert_single_image()`
3. Update preset system and CLI arguments

### New Analysis Modes
1. Extend `near_greyscale_scan.py` with new algorithms
2. Add CLI options in `parse_arguments()`
3. Implement new scanning modes

This codebase demonstrates modern Python practices with comprehensive error handling, performance optimization, and user-friendly features for batch comic book processing.