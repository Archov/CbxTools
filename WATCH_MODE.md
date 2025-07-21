# Watch Mode

CBXTools can monitor an input directory and automatically process new files as they appear, using consolidated utilities for optimal performance and consistency.

## Architecture

Watch mode leverages the consolidated architecture for improved performance:

- **WatchModePackagingWorker**: Specialized packaging worker for watch operations
- **FileSystemUtils**: Unified directory cleanup and file operations
- **ImageAnalyzer**: Consistent image detection across all watchable content
- **ArchiveHandler**: Unified archive detection and processing
- **PathValidator**: Consistent path validation and structure preservation

## Key Features

- **Multi-format Detection**: Automatically detects new CBZ, CBR and CB7 archives as well as loose images or entire image folders
- **Structure Preservation**: Maintains the original directory structure in the output folder using `PathValidator`
- **Optimized Packaging**: Uses `WatchModePackagingWorker` for concurrent image conversion and CBZ creation
- **Persistent History**: Maintains a history file to avoid re-processing files between sessions
- **Smart Cleanup**: Optional deletion of originals with intelligent empty directory removal via `FileSystemUtils`
- **Full Feature Support**: Works with all transformation options including automatic greyscale detection and presets
- **Statistics Integration**: Lifetime statistics are updated as items are processed using consolidated tracking
- **Consistent Logging**: Unified error handling and progress reporting across all operations

## Usage

Use `--watch` with any normal conversion options:

```bash
# Basic watch mode
cbxtools input_dir/ output_dir/ --watch

# Watch with auto-cleanup
cbxtools input_dir/ output_dir/ --watch --delete-originals

# Watch with preset and custom interval
cbxtools input_dir/ output_dir/ --watch --preset manga --watch-interval 10

# Watch with recursive monitoring
cbxtools input_dir/ output_dir/ --watch --recursive
```

## Advanced Options

- `--watch-interval SECONDS`: Check frequency (default: 5 seconds)
- `--delete-originals`: Remove source files after successful conversion
- `--clear-history`: Start with fresh history (re-process all existing files)
- `--recursive`: Monitor subdirectories for new content
- `--keep-originals`: Preserve extracted WebP files alongside CBZ output

## Consolidated Benefits

The refactored watch mode provides enhanced reliability:

- **Unified Error Handling**: Consistent error reporting across all file types
- **Optimized Performance**: Reduced overhead through consolidated utilities
- **Better Resource Management**: Improved memory usage and thread management
- **Enhanced Debugging**: Comprehensive logging for troubleshooting issues
- **Consistent Behavior**: Same processing logic as batch mode operations
