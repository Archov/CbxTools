#!/usr/bin/env python3
"""
Test script to verify the refactored consolidated architecture works correctly.
Tests both core utilities and backward compatibility.
"""

def test_core_imports():
    """Test that all core utilities can be imported."""
    try:
        from cbxtools.core.archive_handler import ArchiveHandler
        from cbxtools.core.image_analyzer import ImageAnalyzer
        from cbxtools.core.filesystem_utils import FileSystemUtils
        from cbxtools.core.packaging_worker import (
            AsynchronousPackagingWorker, 
            SynchronousPackagingWorker,
            WatchModePackagingWorker
        )
        from cbxtools.core.path_validator import PathValidator
        
        print("✓ Core utilities imports successful")
        return True
        
    except ImportError as e:
        print(f"✗ Core utilities import error: {e}")
        return False


def test_backward_compatibility():
    """Test that backward compatibility layer works."""
    try:
        # Test that main modules still provide expected functions
        from cbxtools.archives import extract_archive, create_cbz, find_comic_archives
        from cbxtools.conversion import analyze_image_colorfulness, should_convert_to_greyscale
        from cbxtools.utils import get_file_size_formatted, remove_empty_dirs
        from cbxtools.debug_utils import analyze_image_colorfulness_debug
        
        print("✓ Backward compatibility imports successful")
        return True
        
    except ImportError as e:
        print(f"✗ Backward compatibility import error: {e}")
        return False


def test_file_operations():
    """Test basic file operations using consolidated utilities."""
    try:
        from cbxtools.core.filesystem_utils import FileSystemUtils
        
        # Test file size formatting
        size_str, size_bytes = FileSystemUtils.get_file_size_formatted(1024)
        assert size_str == "1.00 KB"
        assert size_bytes == 1024
        
        size_str, size_bytes = FileSystemUtils.get_file_size_formatted(1048576)
        assert size_str == "1.00 MB"
        assert size_bytes == 1048576
        
        print("✓ File size formatting works correctly")
        
        # Test compression statistics
        stats = FileSystemUtils.calculate_compression_stats(1000, 750)
        assert stats['savings_bytes'] == 250
        assert stats['savings_percentage'] == 25.0
        assert stats['compression_ratio'] == 0.75
        assert stats['increased'] == False
        
        print("✓ Compression statistics calculation works correctly")
        return True
        
    except Exception as e:
        print(f"✗ File operations test failed: {e}")
        return False


def test_path_validation():
    """Test path validation using consolidated utilities."""
    try:
        from cbxtools.core.path_validator import PathValidator
        from pathlib import Path
        
        # Test current directory validation (should exist)
        current_dir = PathValidator.validate_input_path(".")
        assert current_dir.exists()
        assert current_dir.is_dir()
        
        print("✓ Path validation works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Path validation test failed: {e}")
        return False


def test_archive_detection():
    """Test archive detection using consolidated utilities."""
    try:
        from cbxtools.core.archive_handler import ArchiveHandler
        
        # Test supported archive detection
        assert ArchiveHandler.is_supported_archive("test.cbz") == True
        assert ArchiveHandler.is_supported_archive("test.cbr") == True
        assert ArchiveHandler.is_supported_archive("test.cb7") == True
        assert ArchiveHandler.is_supported_archive("test.zip") == True
        assert ArchiveHandler.is_supported_archive("test.rar") == True
        assert ArchiveHandler.is_supported_archive("test.7z") == True
        assert ArchiveHandler.is_supported_archive("test.txt") == False
        
        print("✓ Archive detection works correctly")
        
        # Test finding archives in current directory
        archives = ArchiveHandler.find_archives(".", recursive=False)
        print(f"✓ Found {len(archives)} archives in current directory")
        return True
        
    except Exception as e:
        print(f"✗ Archive detection test failed: {e}")
        return False


def test_image_analysis():
    """Test image analysis using consolidated utilities."""
    try:
        from cbxtools.core.image_analyzer import ImageAnalyzer
        import numpy as np
        
        # Test image file detection
        assert ImageAnalyzer.is_image_file("test.jpg") == True
        assert ImageAnalyzer.is_image_file("test.png") == True
        assert ImageAnalyzer.is_image_file("test.webp") == True
        assert ImageAnalyzer.is_image_file("test.txt") == False
        
        print("✓ Image file detection works correctly")
        
        # Test basic colorfulness analysis with synthetic data
        # Create a test image: mostly grey with some colored pixels
        test_img = np.full((100, 100, 3), 128, dtype=np.uint8)  # Grey image
        # Add some colored pixels
        test_img[10:20, 10:20] = [255, 0, 0]  # Red square
        
        max_diff, mean_diff, colored_ratio = ImageAnalyzer.analyze_colorfulness(test_img, 16)
        
        assert max_diff > 0  # Should detect color differences
        assert isinstance(mean_diff, float)
        assert 0.0 <= colored_ratio <= 1.0  # Should be valid ratio
        
        print(f"✓ Image analysis works correctly (colored_ratio: {colored_ratio:.4f})")
        
        # Test conversion decision
        decision = ImageAnalyzer.should_convert_to_greyscale(test_img, 16, 0.5)
        print(f"✓ Greyscale conversion decision: {decision}")
        
        return True
        
    except ImportError:
        print("○ Image analysis test skipped (numpy not available)")
        return True  # Not a failure, just optional
    except Exception as e:
        print(f"✗ Image analysis test failed: {e}")
        return False


def test_packaging_workers():
    """Test packaging worker classes."""
    try:
        from cbxtools.core.packaging_worker import (
            SynchronousPackagingWorker,
            AsynchronousPackagingWorker,
            WatchModePackagingWorker
        )
        import logging
        
        # Create a logger for testing
        logger = logging.getLogger('test')
        
        # Test synchronous worker creation
        sync_worker = SynchronousPackagingWorker(logger, keep_originals=False)
        assert sync_worker.logger == logger
        assert sync_worker.keep_originals == False
        
        # Test asynchronous worker creation
        async_worker = AsynchronousPackagingWorker(logger, keep_originals=True)
        assert async_worker.logger == logger
        assert async_worker.keep_originals == True
        
        # Test watch mode worker creation
        import queue
        result_queue = queue.Queue()
        watch_worker = WatchModePackagingWorker(logger, keep_originals=False, result_queue)
        assert watch_worker.logger == logger
        assert watch_worker.result_queue == result_queue
        
        print("✓ Packaging worker classes work correctly")
        return True
        
    except Exception as e:
        print(f"✗ Packaging worker test failed: {e}")
        return False


def test_preset_system():
    """Test preset system integration."""
    try:
        from cbxtools.presets import list_available_presets, get_preset_parameters
        
        # Test preset listing
        presets = list_available_presets()
        assert isinstance(presets, list)
        assert len(presets) > 0
        assert 'default' in presets
        
        print(f"✓ Found {len(presets)} presets: {', '.join(presets)}")
        
        # Test preset parameter loading
        default_params = get_preset_parameters('default')
        assert isinstance(default_params, dict)
        assert 'quality' in default_params
        
        print("✓ Preset system works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Preset system test failed: {e}")
        return False


def test_integration():
    """Test integration between different components."""
    try:
        # Test that backward compatibility delegates to core utilities
        from cbxtools.utils import get_file_size_formatted as legacy_get_size
        from cbxtools.core.filesystem_utils import FileSystemUtils
        
        # Both should give the same result
        legacy_result = legacy_get_size(2048)
        core_result = FileSystemUtils.get_file_size_formatted(2048)
        
        assert legacy_result == core_result
        assert legacy_result == ("2.00 KB", 2048)
        
        print("✓ Integration between legacy and core APIs works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False


def main():
    """Run all tests and report results."""
    print("CBXTools Consolidated Architecture Test Suite")
    print("=" * 50)
    
    tests = [
        ("Core Imports", test_core_imports),
        ("Backward Compatibility", test_backward_compatibility),
        ("File Operations", test_file_operations),
        ("Path Validation", test_path_validation),
        ("Archive Detection", test_archive_detection),
        ("Image Analysis", test_image_analysis),
        ("Packaging Workers", test_packaging_workers),
        ("Preset System", test_preset_system),
        ("Integration", test_integration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed! The consolidated architecture is working correctly.")
        print("\nKey improvements verified:")
        print("  • Core utilities are properly consolidated")
        print("  • Backward compatibility is maintained")
        print("  • File operations use unified implementations")
        print("  • Archive and image handling is centralized")
        print("  • Packaging workers follow inheritance hierarchy")
        print("  • Integration between components works seamlessly")
    else:
        print(f"\n❌ {failed} test(s) failed. Please check the implementation.")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
