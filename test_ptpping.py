#!/usr/bin/env python3
"""
Test script for PTPPing installation and basic functionality.
"""

import sys
import subprocess
import importlib
from pathlib import Path


def test_imports():
    """Test if all required modules can be imported."""
    print("Testing module imports...")
    
    required_modules = [
        'numpy',
        'scipy',
        'pyaudio',
        'soundfile',
        'influxdb_client',
        'toml',
        'click',
        'requests'
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"  ✓ {module}")
        except ImportError as e:
            print(f"  ✗ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\nFailed to import: {', '.join(failed_imports)}")
        return False
    
    print("  All required modules imported successfully!")
    return True


def test_ptp_tools():
    """Test if PTP tools are available."""
    print("\nTesting PTP tools...")
    
    ptp_tools = [
        ('ptp4l', 'PTP daemon'),
        ('phc_ctl', 'PTP hardware clock control'),
        ('pmc', 'PTP management client')
    ]
    
    missing_tools = []
    
    for tool, description in ptp_tools:
        try:
            result = subprocess.run([tool, '--help'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"  ✓ {tool} ({description})")
            else:
                print(f"  ✗ {tool} ({description}): command failed")
                missing_tools.append(tool)
        except FileNotFoundError:
            print(f"  ✗ {tool} ({description}): not found")
            missing_tools.append(tool)
        except subprocess.TimeoutExpired:
            print(f"  ✓ {tool} ({description}): available (help timeout)")
    
    if missing_tools:
        print(f"\nMissing PTP tools: {', '.join(missing_tools)}")
        return False
    
    print("  All PTP tools available!")
    return False


def test_audio_devices():
    """Test audio device availability."""
    print("\nTesting audio devices...")
    
    try:
        import pyaudio
        
        audio = pyaudio.PyAudio()
        device_count = audio.get_device_count()
        
        print(f"  Found {device_count} audio devices:")
        
        loopback_devices = []
        
        for i in range(device_count):
            try:
                device_info = audio.get_device_info_by_index(i)
                device_name = device_info['name']
                max_inputs = device_info['maxInputChannels']
                
                if max_inputs > 0:
                    print(f"    {i}: {device_name} (inputs: {max_inputs})")
                    
                    if 'loopback' in device_name.lower():
                        loopback_devices.append(i)
                
            except Exception as e:
                print(f"    {i}: Error getting device info: {e}")
        
        audio.terminate()
        
        if loopback_devices:
            print(f"  ✓ Found {len(loopback_devices)} loopback devices")
            return True
        else:
            print("  ⚠ No loopback devices found (this may cause issues)")
            return False
            
    except ImportError:
        print("  ✗ PyAudio not available")
        return False
    except Exception as e:
        print(f"  ✗ Error testing audio devices: {e}")
        return False


def test_config_file():
    """Test configuration file loading."""
    print("\nTesting configuration...")
    
    config_path = Path("config.toml")
    
    if not config_path.exists():
        print("  ⚠ config.toml not found, using example config")
        config_path = Path("config.toml.example")
    
    if config_path.exists():
        try:
            import toml
            config_data = toml.load(config_path)
            
            required_sections = ['ptp', 'audio', 'network', 'influxdb', 'grafana', 'logging', 'monitoring']
            
            for section in required_sections:
                if section in config_data:
                    print(f"  ✓ {section} section")
                else:
                    print(f"  ✗ Missing {section} section")
                    return False
            
            print("  Configuration file loaded successfully!")
            return True
            
        except Exception as e:
            print(f"  ✗ Error loading configuration: {e}")
            return False
    else:
        print("  ✗ No configuration file found")
        return False


def test_ptp_interface():
    """Test PTP interface configuration."""
    print("\nTesting PTP interface...")
    
    try:
        # Try to get network interfaces
        result = subprocess.run(['ip', 'link', 'show'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            interfaces = []
            for line in result.stdout.splitlines():
                if ':' in line and not line.startswith(' '):
                    interface = line.split(':')[1].strip()
                    if interface and not interface.startswith('lo'):
                        interfaces.append(interface)
            
            print(f"  Available network interfaces: {', '.join(interfaces)}")
            
            # Check if PTP daemon is running
            try:
                result = subprocess.run(['pgrep', 'ptp4l'], 
                                      capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    print("  ✓ PTP daemon (ptp4l) is running")
                    return True
                else:
                    print("  ⚠ PTP daemon (ptp4l) is not running")
                    return False
                    
            except Exception as e:
                print(f"  ⚠ Could not check PTP daemon status: {e}")
                return False
                
        else:
            print("  ✗ Could not enumerate network interfaces")
            return False
            
    except Exception as e:
        print(f"  ✗ Error testing PTP interface: {e}")
        return False


def main():
    """Run all tests."""
    print("PTPPing Installation Test")
    print("=" * 40)
    
    tests = [
        ("Module Imports", test_imports),
        ("PTP Tools", test_ptp_tools),
        ("Audio Devices", test_audio_devices),
        ("Configuration", test_config_file),
        ("PTP Interface", test_ptp_interface)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ✗ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 40)
    print("Test Results Summary")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! PTPPing should work correctly.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please check the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
