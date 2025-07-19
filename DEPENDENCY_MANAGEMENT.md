# CBXTools Dependency Management

CBXTools now includes built-in dependency checking and installation to ensure all required packages are available before processing comic archives.

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
These packages are essential for CBXTools to function:

- **pillow** - Required for image processing and WebP conversion
- **rarfile** - Required for extracting CBR (RAR) archive files  
- **patool** - Required for general archive extraction support

### Optional Dependencies
These packages enable additional features:

- **numpy** - Enhances performance for auto-greyscale image analysis
- **matplotlib** - Enables debug histogram visualizations

## Automatic Dependency Checking

By default, CBXTools will check for required dependencies on startup. If any are missing, you'll be prompted with options to:

1. Install all missing dependencies automatically
2. Install only required dependencies
3. Get manual installation instructions
4. Continue without installing (some features may not work)

## Manual Installation

If automatic installation doesn't work or you prefer to install manually:

```bash
# Install all dependencies
pip install pillow rarfile patool numpy matplotlib

# Install only required dependencies
pip install pillow rarfile patool

# Install from setup.py
pip install -e .
```

## Troubleshooting

### Permission Errors
If you get permission errors during installation, try:

```bash
# Install for current user only
pip install --user pillow rarfile patool

# Or run with elevated privileges (Windows)
# Run command prompt as Administrator, then:
pip install pillow rarfile patool
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

#### patool
The `patool` package works with various archive formats and may require additional utilities:
- For best compatibility, install 7-zip or p7zip
- **Windows**: Install 7-Zip from 7-zip.org
- **Linux**: `sudo apt install p7zip-full`
- **macOS**: `brew install p7zip`

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

## Exit Codes

The dependency management commands return specific exit codes:

- **0**: Success (all required dependencies available)
- **1**: Failure (missing required dependencies or installation failed)

This makes it easy to integrate with scripts and automation tools.
