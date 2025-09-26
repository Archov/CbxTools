# CBXTools Architecture Documentation

This document describes the modular architecture of CBXTools, which was refactored to eliminate code duplication and improve maintainability.

## Overview

CBXTools follows a layered architecture with consolidated core utilities that eliminate denormalization:

```
CLI Layer (cli.py)
    ↓
Application Layer (conversion.py, watchers.py, debug_utils.py)
    ↓
Core Utilities Layer (cbxtools.core.*)
    ↓
Foundation Layer (archives.py, utils.py, stats_tracker.py)
```

## Core Architecture Principles

1. **Single Responsibility**: Each core utility handles one specific domain
2. **DRY (Don't Repeat Yourself)**: Common functionality is centralized
3. **Consistency**: All modules use the same underlying utilities
4. **Backward Compatibility**: Public APIs remain unchanged
5. **Modularity**: Components can be tested and maintained independently

## Core Utilities (`cbxtools.core`)

### ArchiveHandler (`core/archive_handler.py`)

**Purpose**: Unified archive handling for comic book formats

**Key Features**:
- Supports CBZ/CBR/CB7 (ZIP/RAR/7Z) formats
- Consistent extraction and creation logic
- Optimized compression settings
- Error handling and validation

**Main Classes/Methods**:
- `ArchiveHandler.extract_archive()`: Extract any supported archive
- `ArchiveHandler.create_cbz()`: Create CBZ with optimized compression
- `ArchiveHandler.find_archives()`: Locate archives in directories
- `ArchiveHandler.is_supported_archive()`: Validate archive format

**Before Refactoring**: Archive extraction logic was duplicated in `archives.py`, `debug_utils.py`, and `near_greyscale_scan.py`

**After Refactoring**: Single implementation used by all modules

### ImageAnalyzer (`core/image_analyzer.py`)

**Purpose**: Centralized image analysis and auto-greyscale detection

**Key Features**:
- Unified colorfulness analysis algorithms
- Detailed debug statistics generation
- Enhanced B&W conversion with auto-contrast
- Image file detection and enumeration

**Main Classes/Methods**:
- `ImageAnalyzer.analyze_colorfulness()`: Core color analysis
- `ImageAnalyzer.analyze_colorfulness_detailed()`: Extended debug version
- `ImageAnalyzer.should_convert_to_greyscale()`: Conversion decision logic
- `ImageAnalyzer.should_convert_to_greyscale_detailed()`: Debug version
- `ImageAnalyzer.convert_to_bw_with_contrast()`: Enhanced B&W conversion
- `ImageAnalyzer.find_image_files()`: Locate images in directories

**Before Refactoring**: Image analysis logic was duplicated in `conversion.py` and `debug_utils.py` with ~80 lines of redundant code

**After Refactoring**: Single implementation with both production and debug interfaces

### FileSystemUtils (`core/filesystem_utils.py`)

**Purpose**: Unified file system operations and utilities

**Key Features**:
- Consistent file size formatting
- Directory cleanup operations
- Compression statistics calculation
- Path validation and resolution

**Main Classes/Methods**:
- `FileSystemUtils.get_file_size_formatted()`: Human-readable file sizes
- `FileSystemUtils.remove_empty_dirs()`: Recursive directory cleanup
- `FileSystemUtils.cleanup_empty_directories()`: Bulk directory cleanup
- `FileSystemUtils.calculate_compression_stats()`: Compression analysis
- `FileSystemUtils.ensure_directory_exists()`: Directory creation

**Before Refactoring**: File operations were duplicated in `utils.py`, `watchers.py`, and `stats_tracker.py`

**After Refactoring**: Centralized implementation with consistent behavior

### PackagingWorker (`core/packaging_worker.py`)

**Purpose**: Unified packaging worker system for CBZ creation

**Key Features**:
- Base class for different execution contexts
- Synchronous and asynchronous variants
- Watch mode specialized implementation
- Consistent error handling and logging

**Main Classes**:
- `PackagingWorkerBase`: Abstract base class
- `SynchronousPackagingWorker`: For single-threaded operations
- `AsynchronousPackagingWorker`: For pipeline operations
- `WatchModePackagingWorker`: Enhanced for watch mode

**Before Refactoring**: Packaging logic was duplicated in `conversion.py` and `watchers.py` with different implementations

**After Refactoring**: Inheritance hierarchy with specialized implementations

### PathValidator (`core/path_validator.py`)

**Purpose**: Centralized path validation and resolution

**Key Features**:
- Input/output path validation
- File and directory validation
- Extension checking
- Consistent error messages

**Main Classes/Methods**:
- `PathValidator.validate_input_path()`: Input validation
- `PathValidator.validate_output_path()`: Output validation
- `PathValidator.validate_file_path()`: File-specific validation
- `PathValidator.validate_directory_path()`: Directory-specific validation
- `PathValidator.resolve_relative_output_path()`: Structure preservation

**Before Refactoring**: Path validation was scattered across multiple modules with inconsistent error handling

**After Refactoring**: Centralized validation with standardized error messages

## Module Relationships

### Dependency Flow

```
cli.py → PathValidator, FileSystemUtils
↓
conversion.py → ImageAnalyzer, FileSystemUtils, PackagingWorker
↓
watchers.py → ArchiveHandler, ImageAnalyzer, FileSystemUtils, PackagingWorker
↓
debug_utils.py → ImageAnalyzer, ArchiveHandler
↓
archives.py → ArchiveHandler, ImageAnalyzer (compatibility layer)
↓
utils.py → FileSystemUtils (compatibility layer)
```

### Backward Compatibility Layer

To maintain API compatibility, existing modules provide re-export functions:

**archives.py**:
```python
def extract_archive(archive_path, extract_dir, logger):
    return ArchiveHandler.extract_archive(archive_path, extract_dir, logger)
```

**utils.py**:
```python
def get_file_size_formatted(file_path_or_size):
    return FileSystemUtils.get_file_size_formatted(file_path_or_size)
```

**conversion.py**:
```python
def analyze_image_colorfulness(img_array, pixel_threshold=16):
    return ImageAnalyzer.analyze_colorfulness(img_array, pixel_threshold)
```

## Benefits of Refactoring

### Code Reduction
- **~300+ lines** of duplicate code eliminated
- **5 core utilities** replace scattered implementations
- **Consistent APIs** across all modules

### Maintainability Improvements
- **Single source of truth** for each operation type
- **Easier debugging** with centralized logic
- **Simplified testing** of core functionality
- **Reduced cognitive load** when making changes

### Consistency Gains
- **Uniform error handling** across all operations
- **Standardized logging** patterns
- **Consistent parameter validation**
- **Unified compression settings**

### Performance Benefits
- **Optimized algorithms** in single implementations
- **Reduced memory footprint** from eliminated duplication
- **Improved caching** opportunities

## Extension Points

The modular architecture provides clear extension points:

### Adding New Archive Formats
1. Extend `ArchiveHandler` with new format support
2. Update `SUPPORTED_EXTENSIONS` set
3. Add format-specific extraction method

### Adding New Image Analysis
1. Extend `ImageAnalyzer` with new analysis methods
2. Maintain consistency with existing interface patterns
3. Add debug variants for new functionality

### Adding New Packaging Modes
1. Inherit from `PackagingWorkerBase`
2. Implement context-specific logic
3. Follow established error handling patterns

## Testing Strategy

### Unit Testing
- **Core utilities** can be tested independently
- **Mock dependencies** easily with clear interfaces
- **Consistent test patterns** across all modules

### Integration Testing
- **End-to-end workflows** through public APIs
- **Backward compatibility** verification
- **Performance regression** testing

### Debug Testing
- **Debug utilities** provide comprehensive analysis
- **Threshold testing** for auto-greyscale parameters
- **Visualization tools** for algorithm verification

## Migration Guide

For developers working with the codebase:

### Direct Core Usage (Recommended)
```python
from cbxtools.core.image_analyzer import ImageAnalyzer
from cbxtools.core.archive_handler import ArchiveHandler

# Direct usage of consolidated utilities
result = ImageAnalyzer.analyze_colorfulness(img_array)
ArchiveHandler.extract_archive(path, dest, logger)
```

### Legacy Compatibility (Supported)
```python
from cbxtools.conversion import analyze_image_colorfulness
from cbxtools.archives import extract_archive

# Legacy APIs still work through re-export functions
result = analyze_image_colorfulness(img_array)
extract_archive(path, dest, logger)
```

## Future Enhancements

The modular architecture enables future improvements:

1. **Plugin System**: Core utilities provide foundation for plugins
2. **Configuration Management**: Centralized settings through core utilities
3. **Advanced Caching**: Unified caching across all operations
4. **Metrics Collection**: Comprehensive performance monitoring
5. **API Expansion**: RESTful API built on core utilities

This architecture ensures CBXTools remains maintainable, extensible, and efficient as it evolves.
