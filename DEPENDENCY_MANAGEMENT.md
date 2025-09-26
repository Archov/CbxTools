# CBXTools Dependency Management

CBXTools includes built-in dependency checking and installation with a modular architecture that ensures consistent behavior across all components.

## Architecture

The dependency management system is integrated into the consolidated architecture:

- **Centralized Checking**: Single implementation in `cli.py` eliminates duplicate dependency logic
- **Consistent Error Handling**: Unified error messages and validation across all modules
- **Modular Design**: Core utilities handle their own import dependencies gracefully
- **Graceful Degradation**: Optional dependencies are handled consistently throughout the codebase

## Quick Start

### Check Dependencies
To check if all required dependencies are installed:

```bash
cbxtools --check-dependencies
```

### Install Missing Dependencies
To automatically install any missing dependencies:

```bash
cbxtools --install-dependencies
```

### Skip Dependency Check
If you want to skip the automatic dependency check on startup:

```bash
cbxtools --skip-dependency-check input.cbz output/
```

## Dependencies

### Required Dependencies
These packages are essential for CBXTools core functionality:

- **pillow** - Required for image processing and WebP conversion (used by `ImageAnalyzer`)
- **rarfile** - Required for extracting CBR (RAR) archive files (used by `ArchiveHandler`)
- **py7zr** - Required for CB7 (7Z) archive extraction (used by `ArchiveHandler`)

### Optional Dependencies
These packages enable additional features:

- **numpy** - Enhances performance for auto-greyscale image analysis in `ImageAnalyzer`
- **matplotlib** - Enables debug histogram visualizations in debug utilities

## Consolidated Benefits

The refactored dependency management provides:

### Unified Import Handling
- **Core utilities** handle missing dependencies gracefully
- **Consistent error messages** across all modules
- **Single point of truth** for dependency requirements
- **Modular degradation** - missing optional dependencies don't break core functionality

### Enhanced Error Reporting
- **Detailed dependency status** with descriptions of what each package enables
- **Installation guidance** with specific commands for different scenarios
- **Platform-specific instructions** for common installation issues

### Better Integration
- **Watch mode support** - dependency checks work seamlessly with long-running processes
- **Debug tool compatibility** - debug utilities handle missing optional dependencies gracefully
- **Preset integration** - dependency warnings appear when using features requiring missing packages

## Automatic Dependency Checking

By default, CBXTools will check for required dependencies on startup using the consolidated checking system. If any are missing, you'll be prompted with options to:

1. Install all missing dependencies automatically
2. Install only required dependencies
3. Get manual installation instructions
4. Continue without installing (some features may not work)

The consolidated architecture ensures this check is fast and doesn't duplicate work across modules.

## Manual Installation

If automatic installation doesn't work or you prefer to install manually:

```bash
# Install all dependencies (recommended)
pip install pillow rarfile py7zr numpy matplotlib

# Install only required dependencies
pip install pillow rarfile py7zr

# Install from setup.py
pip install -e .
```

## Troubleshooting

### Permission Errors
If you get permission errors during installation, try:

```bash
# Install for current user only
pip install --user pillow rarfile py7zr

# Or run with elevated privileges (Windows)
# Run command prompt as Administrator, then:
pip install pillow rarfile py7zr
```

### Pip Not Available
If pip is not available:

1. **Windows**: Reinstall Python with pip enabled, or download get-pip.py
2. **Linux**: Install python3-pip package (`sudo apt install python3-pip`)
3. **macOS**: Install using Homebrew (`brew install python`) or use get-pip.py

### Specific Package Issues

#### rarfile
The `rarfile` package requires the `unrar` utility for extracting RAR files:
- **Windows**: Download unrar.exe and place in PATH
- **Linux**: `sudo apt install unrar` or `sudo yum install unrar`
- **macOS**: `brew install unrar`

#### py7zr
For CB7 (7Z) archive support:
- Usually installs cleanly with pip
- If issues occur, try updating pip first: `pip install --upgrade pip`

## Examples

### Basic Usage with Dependency Check
```bash
# This will check dependencies and prompt for installation if needed
cbxtools comic.cbz output_folder/

# Check dependencies without processing files
cbxtools --check-dependencies

# Install dependencies and then process
cbxtools --install-dependencies
cbxtools comic.cbz output_folder/
```

### Skip Checks for Automated Scripts
```bash
# Skip dependency check for automated/scripted usage
cbxtools --skip-dependency-check --preset high-quality comics/ output/
```

### Verbose Dependency Information
```bash
# Get detailed information about dependency status
cbxtools --check-dependencies --verbose
```

### Watch Mode with Dependencies
```bash
# Dependency check works seamlessly with watch mode
cbxtools input_dir/ output_dir/ --watch --preset manga

# Skip check for long-running watch processes
cbxtools input_dir/ output_dir/ --watch --skip-dependency-check
```

## Integration with CI/CD

For automated environments, you can check and install dependencies programmatically:

```bash
# Check if dependencies are available (exit code 0 = success)
if cbxtools --check-dependencies; then
    echo "Dependencies OK"
else
    echo "Installing dependencies..."
    cbxtools --install-dependencies
fi

# Then run your processing
cbxtools --skip-dependency-check input/ output/
```

## Core Module Handling

The consolidated architecture handles dependencies at the module level:

### ArchiveHandler
```python
# Gracefully handles missing archive utilities
try:
    import py7zr
except ImportError:
    # CB7 support disabled, clear error message provided
    pass
```

### ImageAnalyzer
```python
# Requires numpy for analysis; raises a clear error if missing
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None
    _HAS_NUMPY = False
```

### Debug Utilities
```python
# Optional visualization support
try:
    import matplotlib
except ImportError:
    # Debug analysis works without visualizations
    matplotlib = None
```

## Exit Codes

The dependency management commands return specific exit codes:

- **0**: Success (all required dependencies available)
- **1**: Failure (missing required dependencies or installation failed)

This makes it easy to integrate with scripts and automation tools while providing consistent behavior across the entire application.
