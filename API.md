# CBXTools API Documentation

This document describes the consolidated API for CBXTools, including both the new core utilities and backward-compatible interfaces.

## Core API (`cbxtools.core`)

The core utilities provide the foundational functionality for CBXTools with clean, consistent interfaces.

### ArchiveHandler

**Module**: `cbxtools.core.archive_handler`

#### Class Methods

##### `ArchiveHandler.extract_archive(archive_path, extract_dir, logger=None)`

Extract a comic archive to a directory.

**Parameters**:
- `archive_path` (Path): Path to the archive file
- `extract_dir` (Path): Directory to extract files to
- `logger` (Logger, optional): Logger for output messages

**Raises**:
- `ValueError`: If archive format is unsupported
- `Exception`: If extraction fails

**Example**:
```python
from cbxtools.core.archive_handler import ArchiveHandler

ArchiveHandler.extract_archive(Path("comic.cbz"), Path("extracted/"), logger)
```

##### `ArchiveHandler.create_cbz(source_dir, output_file, logger=None, compresslevel=9)`

Create a CBZ archive from a directory.

**Parameters**:
- `source_dir` (Path): Source directory containing files
- `output_file` (Path): Output CBZ file path
- `logger` (Logger, optional): Logger for output messages
- `compresslevel` (int): ZIP compression level (0-9)

**Example**:
```python
ArchiveHandler.create_cbz(Path("webp_images/"), Path("output.cbz"), logger, 9)
```

##### `ArchiveHandler.find_archives(directory, recursive=False)`

Find all supported archives in a directory.

**Parameters**:
- `directory` (Path): Directory to search
- `recursive` (bool): Whether to search subdirectories

**Returns**:
- `List[Path]`: Sorted list of archive paths

**Example**:
```python
archives = ArchiveHandler.find_archives(Path("comics/"), recursive=True)
```

##### `ArchiveHandler.is_supported_archive(file_path)`

Check if a file is a supported archive format.

**Parameters**:
- `file_path` (Path): File path to check

**Returns**:
- `bool`: True if supported, False otherwise

### ImageAnalyzer

**Module**: `cbxtools.core.image_analyzer`

#### Class Methods

##### `ImageAnalyzer.analyze_colorfulness(img_array, pixel_threshold=16)`

Analyze image colorfulness for auto-greyscale detection.

**Parameters**:
- `img_array` (numpy.ndarray): RGB image array
- `pixel_threshold` (int): Threshold for colored pixels

**Returns**:
- `Tuple[int, float, float]`: (max_diff, mean_diff, colored_ratio)

**Example**:
```python
from cbxtools.core.image_analyzer import ImageAnalyzer
import numpy as np
from PIL import Image

with Image.open("image.jpg") as img:
    img_array = np.array(img)
    max_diff, mean_diff, colored_ratio = ImageAnalyzer.analyze_colorfulness(img_array)
```

##### `ImageAnalyzer.analyze_colorfulness_detailed(img_array, pixel_threshold=16)`

Detailed colorfulness analysis with extended statistics.

**Parameters**:
- `img_array` (numpy.ndarray): RGB image array
- `pixel_threshold` (int): Threshold for colored pixels

**Returns**:
- `Dict`: Detailed analysis with statistics

**Example**:
```python
analysis = ImageAnalyzer.analyze_colorfulness_detailed(img_array, 16)
print(f"Colored ratio: {analysis['colored_ratio']}")
print(f"Very colored pixels: {analysis['very_colored_pixels']}")
```

##### `ImageAnalyzer.should_convert_to_greyscale(img_array, pixel_threshold=16, percent_threshold=0.01)`

Determine if an image should be converted to greyscale.

**Parameters**:
- `img_array` (numpy.ndarray): RGB image array
- `pixel_threshold` (int): Per-pixel difference threshold
- `percent_threshold` (float): Fraction of colored pixels threshold

**Returns**:
- `bool`: True if should convert to greyscale

##### `ImageAnalyzer.should_convert_to_greyscale_detailed(img_array, pixel_threshold=16, percent_threshold=0.01)`

Detailed greyscale conversion analysis.

**Parameters**:
- `img_array` (numpy.ndarray): RGB image array
- `pixel_threshold` (int): Per-pixel difference threshold
- `percent_threshold` (float): Fraction of colored pixels threshold

**Returns**:
- `Tuple[bool, Dict]`: (decision, detailed_analysis)

##### `ImageAnalyzer.convert_to_bw_with_contrast(img)`

Convert image to black and white with auto-contrast.

**Parameters**:
- `img` (PIL.Image): Input image

**Returns**:
- `PIL.Image`: Enhanced B&W image

##### `ImageAnalyzer.find_image_files(directory, recursive=False)`

Find all image files in a directory.

**Parameters**:
- `directory` (Path): Directory to search
- `recursive` (bool): Whether to search subdirectories

**Returns**:
- `List[Path]`: Sorted list of image paths

##### `ImageAnalyzer.is_image_file(file_path)`

Check if a file is an image.

**Parameters**:
- `file_path` (Path): File path to check

**Returns**:
- `bool`: True if image file, False otherwise

### FileSystemUtils

**Module**: `cbxtools.core.filesystem_utils`

#### Class Methods

##### `FileSystemUtils.get_file_size_formatted(file_path_or_size)`

Get human-readable file size.

**Parameters**:
- `file_path_or_size` (Path or int): File path or size in bytes

**Returns**:
- `Tuple[str, int]`: (formatted_size, size_in_bytes)

**Example**:
```python
from cbxtools.core.filesystem_utils import FileSystemUtils

size_str, size_bytes = FileSystemUtils.get_file_size_formatted(Path("file.cbz"))
print(f"File size: {size_str}")  # e.g., "15.2 MB"
```

##### `FileSystemUtils.remove_empty_dirs(directory, root_dir, logger=None)`

Recursively remove empty directories.

**Parameters**:
- `directory` (Path): Directory to check and remove
- `root_dir` (Path): Root directory (won't be removed)
- `logger` (Logger, optional): Logger for messages

##### `FileSystemUtils.cleanup_empty_directories(root_dir, logger=None)`

Remove all empty directories under root_dir.

**Parameters**:
- `root_dir` (Path): Root directory to clean up
- `logger` (Logger, optional): Logger for messages

##### `FileSystemUtils.calculate_compression_stats(original_size, new_size)`

Calculate compression statistics.

**Parameters**:
- `original_size` (int): Original file size in bytes
- `new_size` (int): Compressed file size in bytes

**Returns**:
- `Dict`: Statistics including savings_bytes, savings_percentage, compression_ratio, increased

### PathValidator

**Module**: `cbxtools.core.path_validator`

#### Class Methods

##### `PathValidator.validate_input_path(input_path_str, must_exist=True)`

Validate and resolve input path.

**Parameters**:
- `input_path_str` (str): Input path string
- `must_exist` (bool): Whether path must exist

**Returns**:
- `Path`: Resolved input path

**Raises**:
- `ValueError`: If path is invalid

##### `PathValidator.validate_output_path(output_path_str, create_if_missing=True)`

Validate and resolve output path.

**Parameters**:
- `output_path_str` (str): Output path string
- `create_if_missing` (bool): Whether to create directory

**Returns**:
- `Path`: Resolved output path

##### `PathValidator.validate_file_path(file_path_str, must_exist=True, extensions=None)`

Validate a file path with optional extension checking.

**Parameters**:
- `file_path_str` (str): File path string
- `must_exist` (bool): Whether file must exist
- `extensions` (Set[str], optional): Allowed extensions with dots

**Returns**:
- `Path`: Resolved file path

### PackagingWorker Classes

**Module**: `cbxtools.core.packaging_worker`

#### SynchronousPackagingWorker

For single-threaded CBZ packaging operations.

```python
from cbxtools.core.packaging_worker import SynchronousPackagingWorker

worker = SynchronousPackagingWorker(logger, keep_originals=False)
success, new_size = worker.process(file_output_dir, cbz_output, input_file)
```

#### AsynchronousPackagingWorker

For pipelined operations with background packaging.

```python
from cbxtools.core.packaging_worker import AsynchronousPackagingWorker

worker = AsynchronousPackagingWorker(logger, keep_originals=False)
worker.start()
worker.queue_package(file_output_dir, cbz_output, input_file, result_dict)
# ... process other files ...
worker.stop()
```

#### WatchModePackagingWorker

Specialized for watch mode operations with result tracking.

```python
from cbxtools.core.packaging_worker import WatchModePackagingWorker
import queue

result_queue = queue.Queue()
worker = WatchModePackagingWorker(logger, keep_originals=False, result_queue)
worker.start()
# Results automatically appear in result_queue
```

## Backward Compatible API

Existing modules provide wrapper functions for backward compatibility.

### archives.py

```python
from cbxtools.archives import extract_archive, create_cbz, find_comic_archives

# These functions delegate to ArchiveHandler
extract_archive(archive_path, extract_dir, logger)
create_cbz(source_dir, output_file, logger, compresslevel=9)
archives = find_comic_archives(directory, recursive=False)
```

### conversion.py

```python
from cbxtools.conversion import analyze_image_colorfulness, should_convert_to_greyscale

# These functions delegate to ImageAnalyzer
max_diff, mean_diff, colored_ratio = analyze_image_colorfulness(img_array, pixel_threshold)
decision = should_convert_to_greyscale(img_array, pixel_threshold, percent_threshold)
```

### utils.py

```python
from cbxtools.utils import get_file_size_formatted, remove_empty_dirs

# These functions delegate to FileSystemUtils
size_str, size_bytes = get_file_size_formatted(file_path)
remove_empty_dirs(directory, root_dir, logger)
```

## Error Handling

All core utilities follow consistent error handling patterns:

### Common Exceptions

- **ValueError**: Invalid parameters or unsupported formats
- **FileNotFoundError**: Missing required files
- **PermissionError**: Insufficient file system permissions
- **ImportError**: Missing required dependencies

### Error Messages

Error messages are consistent and actionable:

```python
try:
    ArchiveHandler.extract_archive(archive_path, extract_dir, logger)
except ValueError as e:
    # e.g., "Unsupported archive format: .xyz"
    logger.error(f"Archive error: {e}")
except Exception as e:
    # e.g., "Permission denied: /path/to/file"
    logger.error(f"Extraction failed: {e}")
```

## Performance Considerations

### Memory Usage

- **ImageAnalyzer**: Processes images in memory; large images may require significant RAM
- **ArchiveHandler**: Extracts to temporary directories; ensure adequate disk space
- **PackagingWorker**: Asynchronous variants reduce memory pressure during batch operations

### Thread Safety

- **Core utilities**: Thread-safe for read operations
- **PackagingWorker**: Designed for concurrent use
- **File operations**: Use appropriate locking for concurrent access

### Optimization Tips

1. **Use AsynchronousPackagingWorker** for batch operations
2. **Enable numpy** for faster image analysis
3. **Set appropriate thread counts** based on CPU cores
4. **Monitor disk space** during large batch operations

## Extension Points

The modular architecture provides clear extension points:

### Adding New Archive Formats

1. Extend `ArchiveHandler.SUPPORTED_EXTENSIONS`
2. Add format-specific extraction method
3. Update `_extract_archive()` dispatch logic

### Adding New Image Analysis

1. Add methods to `ImageAnalyzer`
2. Follow existing naming conventions
3. Provide both simple and detailed variants

### Adding New Packaging Modes

1. Inherit from `PackagingWorkerBase`
2. Implement required abstract methods
3. Follow established error handling patterns

## Testing

### Unit Testing

```python
import unittest
from cbxtools.core.image_analyzer import ImageAnalyzer
import numpy as np

class TestImageAnalyzer(unittest.TestCase):
    def test_analyze_colorfulness(self):
        # Create test image array
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        max_diff, mean_diff, colored_ratio = ImageAnalyzer.analyze_colorfulness(img_array)
        
        self.assertIsInstance(max_diff, int)
        self.assertIsInstance(mean_diff, float)
        self.assertIsInstance(colored_ratio, float)
        self.assertGreaterEqual(colored_ratio, 0.0)
        self.assertLessEqual(colored_ratio, 1.0)
```

### Integration Testing

```python
from cbxtools.core.archive_handler import ArchiveHandler
from cbxtools.core.filesystem_utils import FileSystemUtils
import tempfile
from pathlib import Path

def test_archive_workflow():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test archive extraction
        ArchiveHandler.extract_archive(test_cbz_path, temp_path, logger)
        
        # Verify extraction
        extracted_files = list(temp_path.rglob("*"))
        assert len(extracted_files) > 0
        
        # Test size calculation
        size_str, size_bytes = FileSystemUtils.get_file_size_formatted(test_cbz_path)
        assert size_bytes > 0
        assert "B" in size_str or "KB" in size_str or "MB" in size_str
```

## Migration Guide

### From Legacy API to Core API

**Old Way**:
```python
from cbxtools.conversion import analyze_image_colorfulness
from cbxtools.archives import extract_archive

result = analyze_image_colorfulness(img_array)
extract_archive(archive_path, extract_dir, logger)
```

**New Way**:
```python
from cbxtools.core.image_analyzer import ImageAnalyzer
from cbxtools.core.archive_handler import ArchiveHandler

result = ImageAnalyzer.analyze_colorfulness(img_array)
ArchiveHandler.extract_archive(archive_path, extract_dir, logger)
```

### Gradual Migration Strategy

1. **Phase 1**: Continue using legacy APIs (fully supported)
2. **Phase 2**: Replace imports for new development
3. **Phase 3**: Migrate existing code to core APIs
4. **Phase 4**: Remove legacy compatibility layer (future versions)

## Best Practices

### Code Organization

```python
# Recommended: Import core utilities directly
from cbxtools.core.image_analyzer import ImageAnalyzer
from cbxtools.core.archive_handler import ArchiveHandler
from cbxtools.core.filesystem_utils import FileSystemUtils

# Use consistent error handling
try:
    analysis = ImageAnalyzer.analyze_colorfulness_detailed(img_array)
except Exception as e:
    logger.error(f"Image analysis failed: {e}")
    return None
```

### Resource Management

```python
# Use context managers for temporary directories
with tempfile.TemporaryDirectory() as temp_dir:
    ArchiveHandler.extract_archive(archive_path, temp_dir, logger)
    # Process extracted files
    # Cleanup happens automatically
```

### Logging

```python
# Consistent logging patterns
logger.info(f"Processing archive: {archive_path}")
logger.debug(f"Extraction parameters: {extract_params}")
logger.error(f"Failed to extract {archive_path}: {error}")
```

### Error Recovery

```python
# Graceful error handling with fallbacks
try:
    result = ImageAnalyzer.analyze_colorfulness_detailed(img_array)
except ImportError:
    # numpy not available, use basic analysis
    logger.warning("numpy not available, using basic analysis")
    result = ImageAnalyzer.analyze_colorfulness(img_array)
except Exception as e:
    logger.error(f"Image analysis failed: {e}")
    return default_result
```

This API documentation provides comprehensive coverage of both the new consolidated architecture and backward-compatible interfaces, enabling developers to effectively use and extend CBXTools.
