#!/usr/bin/env python3
"""
Debug utilities for auto-greyscale functionality.
"""

import json
import time
import os
from pathlib import Path
import numpy as np
from PIL import Image


def analyze_image_colorfulness(img_array, pixel_threshold=16, debug=False):
    """
    Analyze if an image is effectively greyscale by checking pixel color variation.
    
    Args:
        img_array: numpy array of image data (RGB)
        pixel_threshold: threshold for considering a pixel "colored"
        debug: if True, return additional debug information
    
    Returns:
        tuple: (max_diff, mean_diff, colored_ratio) or debug dict if debug=True
    """
    # Calculate per-pixel difference between max and min RGB values
    diffs = img_array.max(axis=2).astype(int) - img_array.min(axis=2).astype(int)
    max_diff = int(diffs.max())
    mean_diff = float(diffs.mean())
    colored_pixels = int(np.count_nonzero(diffs > pixel_threshold))
    total_pixels = diffs.size
    colored_ratio = colored_pixels / total_pixels
    
    if debug:
        # Additional debug statistics
        std_diff = float(diffs.std())
        median_diff = float(np.median(diffs))
        percentile_95 = float(np.percentile(diffs, 95))
        percentile_99 = float(np.percentile(diffs, 99))
        
        # Count pixels in different ranges
        very_colored = int(np.count_nonzero(diffs > pixel_threshold * 2))
        slightly_colored = int(np.count_nonzero((diffs > pixel_threshold) & (diffs <= pixel_threshold * 2)))
        
        return {
            'max_diff': max_diff,
            'mean_diff': mean_diff,
            'std_diff': std_diff,
            'median_diff': median_diff,
            'percentile_95': percentile_95,
            'percentile_99': percentile_99,
            'colored_pixels': colored_pixels,
            'very_colored_pixels': very_colored,
            'slightly_colored_pixels': slightly_colored,
            'total_pixels': total_pixels,
            'colored_ratio': colored_ratio,
            'very_colored_ratio': very_colored / total_pixels,
            'slightly_colored_ratio': slightly_colored / total_pixels,
            'pixel_threshold_used': pixel_threshold,
            'image_shape': img_array.shape
        }
    
    return max_diff, mean_diff, colored_ratio


def should_convert_to_greyscale(img_array, pixel_threshold=16, percent_threshold=0.01, debug=False):
    """
    Determine if an image should be converted to greyscale based on color analysis.
    
    Args:
        img_array: numpy array of image data (RGB)
        pixel_threshold: per-pixel difference threshold for "colored" pixels
        percent_threshold: fraction of colored pixels above which image is considered colorful
        debug: if True, return detailed analysis
    
    Returns:
        bool or tuple: True if image should be converted to greyscale, or (decision, debug_info) if debug=True
    """
    if debug:
        analysis = analyze_image_colorfulness(img_array, pixel_threshold, debug=True)
        decision = analysis['colored_ratio'] <= percent_threshold
        analysis['decision'] = decision
        analysis['percent_threshold_used'] = percent_threshold
        analysis['decision_reason'] = f"colored_ratio ({analysis['colored_ratio']:.4f}) {'<=' if decision else '>'} percent_threshold ({percent_threshold})"
        return decision, analysis
    else:
        _, _, colored_ratio = analyze_image_colorfulness(img_array, pixel_threshold, debug=False)
        return colored_ratio <= percent_threshold


def save_debug_analysis(image_path, analysis, output_dir, logger):
    """Save detailed analysis of an image to a debug file."""
    debug_dir = output_dir / 'debug_auto_greyscale'
    debug_dir.mkdir(exist_ok=True)
    
    debug_file = debug_dir / f"{image_path.stem}_analysis.json"
    
    debug_data = {
        'image_file': str(image_path),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'analysis': analysis
    }
    
    try:
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2)
        logger.debug(f"Saved debug analysis to {debug_file}")
    except Exception as e:
        logger.error(f"Failed to save debug analysis: {e}")


def create_debug_visualization(img_array, analysis, image_path, output_dir, logger):
    """Create a visualization showing color distribution for debugging."""
    try:
        debug_dir = output_dir / 'debug_auto_greyscale'
        debug_dir.mkdir(exist_ok=True)
        
        # Calculate difference map
        diffs = img_array.max(axis=2) - img_array.min(axis=2)
        
        # Create visualization
        from PIL import Image as PILImage
        
        # Normalize differences to 0-255 range for visualization
        if diffs.max() > 0:
            diff_normalized = (diffs / diffs.max() * 255).astype(np.uint8)
        else:
            diff_normalized = diffs.astype(np.uint8)
        
        # Create a heatmap-style image
        heatmap = PILImage.fromarray(diff_normalized, mode='L')
        
        # Save the difference visualization
        viz_file = debug_dir / f"{image_path.stem}_diff_heatmap.png"
        heatmap.save(viz_file)
        
        logger.debug(f"Saved difference heatmap to {viz_file}")
        
        # Create a histogram of differences
        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(10, 6))
            plt.hist(diffs.flatten(), bins=50, alpha=0.7, edgecolor='black')
            plt.axvline(analysis['pixel_threshold_used'], color='red', linestyle='--', 
                       label=f"Pixel threshold ({analysis['pixel_threshold_used']})")
            plt.xlabel('RGB Difference (max - min)')
            plt.ylabel('Pixel Count')
            plt.title(f"Color Difference Distribution\\n{image_path.name}")
            plt.legend()
            
            # Add statistics text
            stats_text = f"""
Decision: {'Convert to Greyscale' if analysis['decision'] else 'Keep Color'}
Colored Ratio: {analysis['colored_ratio']:.4f} ({'≤' if analysis['decision'] else '>'} {analysis['percent_threshold_used']})
Max Diff: {analysis['max_diff']}
Mean Diff: {analysis['mean_diff']:.2f}
Colored Pixels: {analysis['colored_pixels']:,} / {analysis['total_pixels']:,}
"""
            plt.text(0.02, 0.98, stats_text.strip(), transform=plt.gca().transAxes, 
                    verticalalignment='top', fontsize=9, 
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            hist_file = debug_dir / f"{image_path.stem}_histogram.png"
            plt.savefig(hist_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.debug(f"Saved histogram to {hist_file}")
            
        except ImportError as e:
            logger.warning(f"Cannot create histogram (missing matplotlib): {e}")
        
    except Exception as e:
        logger.error(f"Failed to create debug visualization: {e}")


def debug_single_file_greyscale(file_path, output_dir=None, 
                                pixel_threshold=16, percent_threshold=0.01, logger=None):
    """
    Perform detailed analysis of a single image or CBZ/CBR file for auto-greyscale debugging.
    
    Args:
        file_path: Path to the image or CBZ/CBR file to analyze
        output_dir: Directory to save debug files (default: same directory as file)
        pixel_threshold: Pixel difference threshold
        percent_threshold: Percentage threshold  
        logger: Logger instance
    
    Returns:
        dict: Detailed analysis results
    """
    from pathlib import Path
    
    file_path = Path(file_path)
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return None
    
    # Check if it's a CBZ/CBR file or an image
    file_ext = file_path.suffix.lower()
    is_archive = file_ext in {'.cbz', '.cbr', '.zip', '.rar'}
    
    if is_archive:
        return debug_archive_greyscale(file_path, output_dir, pixel_threshold, percent_threshold, logger)
    else:
        return debug_single_image_greyscale(file_path, output_dir, pixel_threshold, percent_threshold, logger)


def debug_archive_greyscale(archive_path, output_dir=None, 
                           pixel_threshold=16, percent_threshold=0.01, logger=None):
    """
    Perform detailed analysis of all images in a CBZ/CBR archive for auto-greyscale debugging.
    
    Args:
        archive_path: Path to the CBZ/CBR archive to analyze
        output_dir: Directory to save debug files
        pixel_threshold: Pixel difference threshold
        percent_threshold: Percentage threshold  
        logger: Logger instance
    
    Returns:
        dict: Summary analysis results for the archive
    """
    from PIL import Image
    import numpy as np
    import json
    import tempfile
    from pathlib import Path
    
    archive_path = Path(archive_path)
    if output_dir is None:
        output_dir = archive_path.parent
    else:
        output_dir = Path(output_dir)
    
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info(f"Analyzing CBZ/CBR archive: {archive_path}")
    logger.info(f"Parameters: pixel_threshold={pixel_threshold}, percent_threshold={percent_threshold}")
    
    # Create debug directory for this archive
    archive_debug_dir = output_dir / 'debug_auto_greyscale' / archive_path.stem
    archive_debug_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract the archive
            try:
                import zipfile
                import patoolib
                
                file_ext = archive_path.suffix.lower()
                if file_ext in ('.cbz', '.zip'):
                    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_path)
                elif file_ext in ('.cbr', '.rar'):
                    patoolib.extract_archive(str(archive_path), outdir=str(temp_path))
                else:
                    logger.error(f"Unsupported archive format: {file_ext}")
                    return None
            except Exception as e:
                logger.error(f"Error extracting archive: {e}")
                return None
            
            # Find all image files
            image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
            image_files = []
            
            for root, _, files in os.walk(temp_path):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in image_exts:
                        image_files.append(file_path)
            
            image_files.sort()
            
            if not image_files:
                logger.error(f"No image files found in archive: {archive_path}")
                return None
            
            logger.info(f"Found {len(image_files)} images in archive")
            
            # Analyze each image
            results = []
            convert_count = 0
            keep_count = 0
            total_pixels = 0
            total_colored_pixels = 0
            
            for i, img_file in enumerate(image_files, 1):
                try:
                    logger.info(f"[{i}/{len(image_files)}] Analyzing: {img_file.name}")
                    
                    with Image.open(img_file) as img:
                        # Convert to RGB if needed
                        if img.mode not in ('RGB', 'RGBA', 'L', 'LA'):
                            img = img.convert('RGB')
                        
                        if img.mode in ('RGB', 'RGBA'):
                            img_array = np.array(img)
                            
                            # Perform analysis
                            decision, analysis = should_convert_to_greyscale(
                                img_array, pixel_threshold, percent_threshold, debug=True
                            )
                            
                            # Track statistics
                            if decision:
                                convert_count += 1
                                decision_str = "→ GREYSCALE"
                            else:
                                keep_count += 1
                                decision_str = "→ COLOR"
                            
                            total_pixels += analysis['total_pixels']
                            total_colored_pixels += analysis['colored_pixels']
                            
                            logger.info(f"  Result: {decision_str} (colored_ratio: {analysis['colored_ratio']:.4f})")
                            
                            # Save detailed analysis for this image
                            img_debug_file = archive_debug_dir / f"{img_file.stem}_analysis.json"
                            debug_data = {
                                'archive_file': str(archive_path),
                                'image_file': img_file.name,
                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                                'analysis': analysis
                            }
                            
                            with open(img_debug_file, 'w', encoding='utf-8') as f:
                                json.dump(debug_data, f, indent=2)
                            
                            # Create visualization for this image
                            create_debug_visualization(img_array, analysis, img_file, archive_debug_dir, logger)
                            
                            results.append({
                                'filename': img_file.name,
                                'decision': decision,
                                'colored_ratio': analysis['colored_ratio'],
                                'colored_pixels': analysis['colored_pixels'],
                                'total_pixels': analysis['total_pixels'],
                                'max_diff': analysis['max_diff'],
                                'mean_diff': analysis['mean_diff']
                            })
                            
                        else:
                            logger.info(f"  Skipping: {img_file.name} (already greyscale mode: {img.mode})")
                            results.append({
                                'filename': img_file.name,
                                'decision': None,
                                'already_greyscale': True,
                                'mode': img.mode
                            })
                
                except Exception as e:
                    logger.error(f"  Error analyzing {img_file.name}: {e}")
                    results.append({
                        'filename': img_file.name,
                        'error': str(e)
                    })
            
            # Generate summary
            total_analyzed = convert_count + keep_count
            if total_analyzed > 0:
                convert_pct = (convert_count / total_analyzed) * 100
                overall_colored_ratio = total_colored_pixels / total_pixels if total_pixels > 0 else 0
                
                logger.info("\n" + "=" * 60)
                logger.info(f"ARCHIVE ANALYSIS SUMMARY: {archive_path.name}")
                logger.info("=" * 60)
                logger.info(f"Total images analyzed: {total_analyzed}")
                logger.info(f"Would convert to greyscale: {convert_count} ({convert_pct:.1f}%)")
                logger.info(f"Would keep in color: {keep_count} ({100-convert_pct:.1f}%)")
                logger.info(f"Overall colored ratio: {overall_colored_ratio:.4f}")
                logger.info(f"Parameters used: pixel_threshold={pixel_threshold}, percent_threshold={percent_threshold}")
                
                # Statistics for converted vs kept
                converted_results = [r for r in results if r.get('decision') == True]
                kept_results = [r for r in results if r.get('decision') == False]
                
                if converted_results:
                    avg_converted_ratio = sum(r['colored_ratio'] for r in converted_results) / len(converted_results)
                    logger.info(f"Average colored ratio (converted): {avg_converted_ratio:.4f}")
                
                if kept_results:
                    avg_kept_ratio = sum(r['colored_ratio'] for r in kept_results) / len(kept_results)
                    logger.info(f"Average colored ratio (kept): {avg_kept_ratio:.4f}")
                
                logger.info("=" * 60)
                
                # Save archive summary
                summary = {
                    'archive_file': str(archive_path),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'parameters': {
                        'pixel_threshold': pixel_threshold,
                        'percent_threshold': percent_threshold
                    },
                    'summary': {
                        'total_images': len(image_files),
                        'total_analyzed': total_analyzed,
                        'convert_count': convert_count,
                        'keep_count': keep_count,
                        'convert_percentage': convert_pct,
                        'overall_colored_ratio': overall_colored_ratio
                    },
                    'images': results
                }
                
                summary_file = archive_debug_dir / 'archive_analysis_summary.json'
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2)
                
                logger.info(f"\nDetailed analysis saved to: {archive_debug_dir}")
                return summary
            
            return None
            
    except Exception as e:
        logger.error(f"Error analyzing archive: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def debug_single_image_greyscale(image_path, output_dir=None, 
                                pixel_threshold=16, percent_threshold=0.01, logger=None):
    """
    Perform detailed analysis of a single image for auto-greyscale debugging.
    
    Args:
        image_path: Path to the image to analyze
        output_dir: Directory to save debug files (default: same directory as image)
        pixel_threshold: Pixel difference threshold
        percent_threshold: Percentage threshold  
        logger: Logger instance
    
    Returns:
        dict: Detailed analysis results
    """
    from PIL import Image
    import numpy as np
    import json
    from pathlib import Path
    
    image_path = Path(image_path)
    if output_dir is None:
        output_dir = image_path.parent
    else:
        output_dir = Path(output_dir)
    
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)
    
    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return None
    
    logger.info(f"Analyzing image: {image_path}")
    logger.info(f"Parameters: pixel_threshold={pixel_threshold}, percent_threshold={percent_threshold}")
    
    try:
        # Load and analyze image
        with Image.open(image_path) as img:
            logger.info(f"Image info: size={img.size}, mode={img.mode}, format={img.format}")
            
            # Convert to RGB if needed
            if img.mode not in ('RGB', 'RGBA', 'L', 'LA'):
                logger.info(f"Converting from {img.mode} to RGB")
                img = img.convert('RGB')
            
            if img.mode in ('RGB', 'RGBA'):
                img_array = np.array(img)
                
                # Perform detailed analysis
                decision, analysis = should_convert_to_greyscale(
                    img_array, pixel_threshold, percent_threshold, debug=True
                )
                
                # Print detailed results
                logger.info("=== AUTO-GREYSCALE ANALYSIS RESULTS ===")
                logger.info(f"Decision: {'CONVERT TO GREYSCALE' if decision else 'KEEP COLOR'}")
                logger.info(f"Reason: {analysis['decision_reason']}")
                logger.info("")
                logger.info("Image Statistics:")
                logger.info(f"  Dimensions: {analysis['image_shape'][1]}x{analysis['image_shape'][0]} pixels")
                logger.info(f"  Total pixels: {analysis['total_pixels']:,}")
                logger.info("")
                logger.info("Color Difference Analysis:")
                logger.info(f"  Max difference: {analysis['max_diff']}")
                logger.info(f"  Mean difference: {analysis['mean_diff']:.2f}")
                logger.info(f"  Std deviation: {analysis['std_diff']:.2f}")
                logger.info(f"  Median difference: {analysis['median_diff']:.2f}")
                logger.info(f"  95th percentile: {analysis['percentile_95']:.2f}")
                logger.info(f"  99th percentile: {analysis['percentile_99']:.2f}")
                logger.info("")
                logger.info("Pixel Classification:")
                logger.info(f"  Colored pixels (>{pixel_threshold}): {analysis['colored_pixels']:,} ({analysis['colored_ratio']:.4f})")
                logger.info(f"  Very colored pixels (>{pixel_threshold*2}): {analysis['very_colored_pixels']:,} ({analysis['very_colored_ratio']:.4f})")
                logger.info(f"  Slightly colored pixels ({pixel_threshold}-{pixel_threshold*2}): {analysis['slightly_colored_pixels']:,} ({analysis['slightly_colored_ratio']:.4f})")
                logger.info(f"  Greyscale pixels (≤{pixel_threshold}): {analysis['total_pixels'] - analysis['colored_pixels']:,} ({1 - analysis['colored_ratio']:.4f})")
                logger.info("")
                logger.info("Thresholds:")
                logger.info(f"  Pixel threshold: {analysis['pixel_threshold_used']}")
                logger.info(f"  Percent threshold: {analysis['percent_threshold_used']}")
                logger.info("=" * 45)
                
                # Save detailed analysis
                save_debug_analysis(image_path, analysis, output_dir, logger)
                
                # Create visualizations
                create_debug_visualization(img_array, analysis, image_path, output_dir, logger)
                
                # Additional recommendations
                logger.info("\nRecommendations:")
                if decision:
                    if analysis['colored_ratio'] < percent_threshold * 0.1:
                        logger.info("  ✓ Strong candidate for greyscale conversion (very low color content)")
                    else:
                        logger.info("  ✓ Borderline candidate - consider adjusting thresholds if result seems wrong")
                else:
                    if analysis['colored_ratio'] > percent_threshold * 10:
                        logger.info("  ✗ Clear color image - should not be converted")
                    else:
                        logger.info("  ✗ Borderline case - you might want to:")
                        logger.info(f"    - Increase pixel threshold above {pixel_threshold} for more aggressive detection")
                        logger.info(f"    - Increase percent threshold above {percent_threshold} for more lenient conversion")
                
                # Suggest threshold adjustments
                logger.info("\nThreshold Adjustment Suggestions:")
                if analysis['colored_ratio'] > percent_threshold and analysis['colored_ratio'] < percent_threshold * 2:
                    new_percent = analysis['colored_ratio'] * 1.2
                    logger.info(f"  To convert this image: --auto-greyscale-percent-threshold {new_percent:.4f}")
                
                if analysis['max_diff'] > pixel_threshold and analysis['mean_diff'] < pixel_threshold:
                    new_pixel = int(analysis['percentile_95'] * 1.2)
                    logger.info(f"  For similar images with few color highlights: --auto-greyscale-pixel-threshold {new_pixel}")
                
                return analysis
                
            else:
                logger.info(f"Image is already greyscale (mode: {img.mode})")
                return {'already_greyscale': True, 'mode': img.mode}
                
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def test_threshold_ranges(image_path, output_dir=None, logger=None):
    """
    Test a range of threshold values on a single image to help tune parameters.
    
    Args:
        image_path: Path to test image
        output_dir: Directory for output files
        logger: Logger instance
    """
    from pathlib import Path
    import json
    
    image_path = Path(image_path)
    if output_dir is None:
        output_dir = image_path.parent / 'threshold_tests'
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(exist_ok=True)
    
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)
    
    # Test different pixel thresholds
    pixel_thresholds = [8, 12, 16, 20, 24, 32]
    percent_thresholds = [0.005, 0.01, 0.015, 0.02, 0.03, 0.05]
    
    results = []
    
    logger.info(f"Testing threshold ranges on: {image_path.name}")
    logger.info("Pixel Threshold | Percent Threshold | Decision | Colored Ratio")
    logger.info("-" * 65)
    
    for pixel_thresh in pixel_thresholds:
        for percent_thresh in percent_thresholds:
            analysis = debug_single_image_greyscale(
                image_path, output_dir, pixel_thresh, percent_thresh, 
                logger=logging.getLogger('quiet')  # Suppress verbose output
            )
            
            if analysis and 'decision' in analysis:
                decision_str = "Convert" if analysis['decision'] else "Keep"
                logger.info(f"{pixel_thresh:14d} | {percent_thresh:16.3f} | {decision_str:8s} | {analysis['colored_ratio']:.6f}")
                
                results.append({
                    'pixel_threshold': pixel_thresh,
                    'percent_threshold': percent_thresh,
                    'decision': analysis['decision'],
                    'colored_ratio': analysis['colored_ratio'],
                    'colored_pixels': analysis['colored_pixels']
                })
    
    # Save results
    results_file = output_dir / f"{image_path.stem}_threshold_test_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nDetailed results saved to: {results_file}")
    return results


def analyze_directory_for_auto_greyscale(directory_path, pixel_threshold=16, 
                                        percent_threshold=0.01, logger=None):
    """
    Analyze all images in a directory to see auto-greyscale detection results.
    Useful for batch testing threshold settings.
    
    Args:
        directory_path: Directory containing images
        pixel_threshold: Pixel difference threshold
        percent_threshold: Percentage threshold
        logger: Logger instance
    
    Returns:
        dict: Summary statistics
    """
    from pathlib import Path
    import json
    
    directory_path = Path(directory_path)
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)
    
    # Look for both image files and CBZ/CBR archives
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    archive_exts = {'.cbz', '.cbr', '.zip', '.rar'}
    
    files_to_analyze = []
    for f in directory_path.glob('*'):
        if f.suffix.lower() in image_exts or f.suffix.lower() in archive_exts:
            files_to_analyze.append(f)
    
    if not files_to_analyze:
        logger.error(f"No image files or CBZ/CBR archives found in {directory_path}")
        return None
    
    logger.info(f"Analyzing {len(files_to_analyze)} files in {directory_path}")
    logger.info(f"Using thresholds: pixel={pixel_threshold}, percent={percent_threshold}")
    
    results = []
    convert_count = 0
    keep_count = 0
    error_count = 0
    
    for file_to_analyze in sorted(files_to_analyze):
        try:
            analysis = debug_single_file_greyscale(
                file_to_analyze, directory_path / 'debug_batch', 
                pixel_threshold, percent_threshold,
                logger=logger  # Use the actual logger instead of creating a quiet one
            )
            
            if analysis:
                if file_to_analyze.suffix.lower() in archive_exts:
                    # Handle archive results
                    archive_summary = analysis.get('summary', {})
                    archive_convert_count = archive_summary.get('convert_count', 0)
                    archive_keep_count = archive_summary.get('keep_count', 0)
                    archive_total = archive_convert_count + archive_keep_count
                    
                    if archive_total > 0:
                        convert_count += archive_convert_count
                        keep_count += archive_keep_count
                        
                        convert_pct = (archive_convert_count / archive_total) * 100
                        decision_str = f"→ {archive_convert_count}/{archive_total} GREYSCALE ({convert_pct:.1f}%)"
                        
                        logger.info(f"{file_to_analyze.name:30s} | archive | {decision_str}")
                        
                        results.append({
                            'filename': file_to_analyze.name,
                            'type': 'archive',
                            'convert_count': archive_convert_count,
                            'keep_count': archive_keep_count,
                            'convert_percentage': convert_pct,
                            'overall_colored_ratio': archive_summary.get('overall_colored_ratio', 0)
                        })
                    else:
                        error_count += 1
                        logger.warning(f"Could not analyze archive: {file_to_analyze.name}")
                        
                elif 'decision' in analysis:
                    # Handle single image results
                    if analysis['decision']:
                        convert_count += 1
                        decision_str = "→ GREYSCALE"
                    else:
                        keep_count += 1
                        decision_str = "→ COLOR"
                    
                    logger.info(f"{file_to_analyze.name:30s} | ratio:{analysis['colored_ratio']:.4f} | {decision_str}")
                    results.append({
                        'filename': file_to_analyze.name,
                        'type': 'image',
                        'decision': analysis['decision'],
                        'colored_ratio': analysis['colored_ratio'],
                        'max_diff': analysis['max_diff'],
                        'mean_diff': analysis['mean_diff']
                    })  
                else:
                    error_count += 1
                    logger.warning(f"Could not analyze: {file_to_analyze.name}")
            else:
                error_count += 1
                logger.warning(f"Could not analyze: {file_to_analyze.name}")
                
        except Exception as e:
            error_count += 1
            logger.error(f"Error analyzing {file_to_analyze.name}: {e}")
    
    # Summary statistics
    total_analyzed = convert_count + keep_count
    if total_analyzed > 0:
        convert_pct = (convert_count / total_analyzed) * 100
        
        # Calculate statistics for converted vs kept images
        converted_ratios = [r['colored_ratio'] for r in results if r['decision']]
        kept_ratios = [r['colored_ratio'] for r in results if not r['decision']]
        
        logger.info("\n" + "=" * 60)
        logger.info("BATCH ANALYSIS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total images analyzed: {total_analyzed}")
        logger.info(f"Would convert to greyscale: {convert_count} ({convert_pct:.1f}%)")
        logger.info(f"Would keep in color: {keep_count} ({100-convert_pct:.1f}%)")
        logger.info(f"Errors: {error_count}")
        
        if converted_ratios:
            avg_converted = sum(converted_ratios) / len(converted_ratios)
            max_converted = max(converted_ratios)
            logger.info(f"Converted images - avg colored ratio: {avg_converted:.4f}, max: {max_converted:.4f}")
        
        if kept_ratios:
            avg_kept = sum(kept_ratios) / len(kept_ratios)
            min_kept = min(kept_ratios)
            logger.info(f"Color images - avg colored ratio: {avg_kept:.4f}, min: {min_kept:.4f}")
        
        logger.info("=" * 60)
        
        # Save summary
        summary = {
            'parameters': {
                'pixel_threshold': pixel_threshold,
                'percent_threshold': percent_threshold
            },
            'summary': {
                'total_analyzed': total_analyzed,
                'convert_count': convert_count,
                'keep_count': keep_count,
                'error_count': error_count,
                'convert_percentage': convert_pct
            },
            'results': results
        }
        
        summary_file = directory_path / 'debug_batch' / 'batch_analysis_summary.json'
        summary_file.parent.mkdir(exist_ok=True)
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Detailed summary saved to: {summary_file}")
        return summary
    
    return None
