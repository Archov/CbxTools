import os
import concurrent.futures
from PIL import Image, ImageOps

# Set these paths directly in the script
INPUT_FOLDER = r"D:\\work or something\\watch"
OUTPUT_FOLDER = r"D:\\work or something\\watch\\Out"
# Number of worker threads to use (adjust based on your CPU)
NUM_WORKERS = 32

def process_image(jpg_file):
    input_path = os.path.join(INPUT_FOLDER, jpg_file)
    
    # Create output filename (replace extension with .png)
    output_filename = os.path.splitext(jpg_file)[0] + '.png'
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    
    try:
        # Open image
        with Image.open(input_path) as img:
            # First convert to black and white (grayscale)
            bw_img = img.convert('L')
            
            # Then apply auto contrast to the black and white image
            enhanced_bw_img = ImageOps.autocontrast(bw_img)
            
            # Save as PNG
            enhanced_bw_img.save(output_path, 'PNG')
        
        return f"Converted: {jpg_file} -> {output_filename}"
    except Exception as e:
        return f"Error converting {jpg_file}: {e}"

# Create output folder if it doesn't exist
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# Get all jpg files in the input folder
jpg_files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.jpg', '.jpeg'))]

if not jpg_files:
    print("No JPG files found in the input folder.")
else:
    print(f"Found {len(jpg_files)} JPG files. Starting conversion with {NUM_WORKERS} workers...")
    
    # Process files in parallel using a thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # Submit all tasks and get future objects
        future_to_file = {executor.submit(process_image, jpg_file): jpg_file for jpg_file in jpg_files}
        
        # Process results as they complete
        completed = 0
        for future in concurrent.futures.as_completed(future_to_file):
            result = future.result()
            completed += 1
            print(f"[{completed}/{len(jpg_files)}] {result}")
    
    print(f"Conversion complete. {len(jpg_files)} files processed.")