import os
import json
import time
from ai_android_tester_poc.utils.appium_handler import AppiumHandler, AppiumBy
from ai_android_tester_poc.utils.test_case_generator import TestCaseGenerator

# Google Clock app capabilities
CLOCK_CAPABILITIES = {
    'platformName': 'Android',
    'automationName': 'UiAutomator2',
    'deviceName': 'test_emulator',  # Use your emulator name
    'appPackage': 'com.google.android.deskclock',
    'appActivity': 'com.android.deskclock.DeskClock',
    'noReset': True,
    'fullReset': False,
    'language': 'en',
    'locale': 'US'
}

def main():
    print("Starting test case generation...")
    
    # Initialize Appium handler
    handler = AppiumHandler(capabilities=CLOCK_CAPABILITIES)
    try:
        # Start the Appium driver
        handler.start_driver()
        print("Appium driver started successfully")
        
        # Initialize test case generator
        generator = TestCaseGenerator(handler)
        print("Test case generator initialized")
        
        # Crawl the app and generate test cases
        print("\nStarting app crawl and test case generation...")
        test_cases = generator.crawl_app(max_screens=10)
        
        # Save generated test cases
        output_file = "generated_test_cases.json"
        generator.save_test_cases(test_cases, output_file)
        
        print(f"\nGenerated {len(test_cases)} test cases")
        print(f"Test cases saved to {output_file}")
        
    except Exception as e:
        print(f"Error during test case generation: {e}")
    finally:
        # Clean up
        handler.stop_driver()
        print("\nTest case generation completed")

if __name__ == "__main__":
    main() 