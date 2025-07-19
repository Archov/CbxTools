# Watch Mode

CBXTools can monitor an input directory and automatically process new files as they appear.

## Key Features

- Detects new CBZ, CBR and CB7 archives as well as loose images or entire image folders
- Preserves the original directory structure in the output folder
- Uses a dedicated packaging thread so image conversion and CBZ creation run concurrently
- Maintains a history file to avoid re-processing files between sessions
- Optional deletion of originals once conversion succeeds
- Works with all transformation options including automatic greyscale detection and presets
- Lifetime statistics are updated as items are processed

Use `--watch` with any normal conversion options. Combine with `--delete-originals` to clean up the source directory automatically.
