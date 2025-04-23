import json
import os
import time
from typing import Dict, Any, List
from ai_android_tester_poc.utils.appium_handler import AppiumHandler, AppiumBy

class TestRunner:
    def __init__(self, appium_handler: AppiumHandler):
        self.appium_handler = appium_handler
        self.test_results = []

    def load_test_cases(self, filename: str = "generated_test_cases.json") -> List[Dict[str, Any]]:
        """Loads test cases from a JSON file."""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading test cases: {e}")
            return []

    def execute_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a single test case and returns the result."""
        print(f"\nExecuting test case: {test_case['test_case_id']} - {test_case['title']}")
        result = {
            "test_case_id": test_case["test_case_id"],
            "title": test_case["title"],
            "status": "PASSED",
            "steps_executed": [],
            "failures": []
        }

        try:
            # Execute each step in the test case
            for step in test_case["steps"]:
                print(f"\nExecuting step {step['step_number']}: {step['action']}")
                step_result = self._execute_step(step)
                result["steps_executed"].append(step_result)

                if step_result["status"] == "FAILED":
                    result["status"] = "FAILED"
                    result["failures"].append({
                        "step": step["step_number"],
                        "error": step_result["error"]
                    })

            # Verify assertions
            for assertion in test_case.get("assertions", []):
                print(f"\nVerifying assertion: {assertion}")
                assertion_result = self._verify_assertion(assertion)
                if not assertion_result["passed"]:
                    result["status"] = "FAILED"
                    result["failures"].append({
                        "assertion": assertion,
                        "error": assertion_result["error"]
                    })

        except Exception as e:
            result["status"] = "FAILED"
            result["failures"].append({
                "error": f"Unexpected error: {str(e)}"
            })

        return result

    def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a single step of a test case."""
        result = {
            "step_number": step["step_number"],
            "action": step["action"],
            "status": "PASSED",
            "error": None
        }

        try:
            element = step["element"]
            action_type = step["action"].lower()

            # Print step details
            print(f"\nExecuting step {step['step_number']}:")
            print(f"Action: {action_type}")
            print(f"Element details: {element}")

            # Handle time picker elements
            if "hour" in action_type.lower():
                # For hour selection, we need to find the hour text view
                hour_value = element.get("value", "").lstrip("0")  # Remove leading zero if present
                print(f"Looking for hour element with value: {hour_value}")
                hour_element = self.appium_handler.find_element(
                    AppiumBy.XPATH,
                    f"//android.widget.TextView[@resource-id='com.google.android.deskclock:id/material_hour_tv' and @text='{hour_value}']"
                )
                if hour_element:
                    print(f"Found hour element: {hour_element.get_attribute('text')}")
                    hour_element.click()
                else:
                    # Print all visible hour elements for debugging
                    all_hours = self.appium_handler.find_elements(
                        AppiumBy.XPATH,
                        "//android.widget.TextView[@resource-id='com.google.android.deskclock:id/material_hour_tv']"
                    )
                    print("Available hour elements:")
                    for h in all_hours:
                        print(f"- {h.get_attribute('text')}")
                    raise ValueError(f"Could not find hour element with value {hour_value}")

            elif "am" in action_type.lower() or "pm" in action_type.lower():
                # For AM/PM selection
                period = "AM" if "am" in action_type.lower() else "PM"
                print(f"Looking for {period} button")
                period_button = self.appium_handler.find_element(
                    AppiumBy.ID,
                    f"com.google.android.deskclock:id/material_clock_period_{period.lower()}_button"
                )
                if period_button:
                    print(f"Found {period} button")
                    period_button.click()
                else:
                    # Print all visible period buttons for debugging
                    all_periods = self.appium_handler.find_elements(
                        AppiumBy.XPATH,
                        "//android.widget.Button[contains(@resource-id, 'material_clock_period_')]"
                    )
                    print("Available period buttons:")
                    for p in all_periods:
                        print(f"- {p.get_attribute('text')}")
                    raise ValueError(f"Could not find {period} button")

            elif "ok" in action_type.lower():
                # For OK button
                print("Looking for OK button")
                ok_button = self.appium_handler.find_element(
                    AppiumBy.ID,
                    "com.google.android.deskclock:id/material_timepicker_ok_button"
                )
                if ok_button:
                    print("Found OK button")
                    ok_button.click()
                else:
                    # Print all visible buttons for debugging
                    all_buttons = self.appium_handler.find_elements(
                        AppiumBy.XPATH,
                        "//android.widget.Button"
                    )
                    print("Available buttons:")
                    for b in all_buttons:
                        print(f"- {b.get_attribute('text')} (id: {b.get_attribute('resource-id')})")
                    raise ValueError("Could not find OK button")

            elif "cancel" in action_type.lower():
                # For Cancel button
                print("Looking for Cancel button")
                cancel_button = self.appium_handler.find_element(
                    AppiumBy.ID,
                    "com.google.android.deskclock:id/material_timepicker_cancel_button"
                )
                if cancel_button:
                    print("Found Cancel button")
                    cancel_button.click()
                else:
                    # Print all visible buttons for debugging
                    all_buttons = self.appium_handler.find_elements(
                        AppiumBy.XPATH,
                        "//android.widget.Button"
                    )
                    print("Available buttons:")
                    for b in all_buttons:
                        print(f"- {b.get_attribute('text')} (id: {b.get_attribute('resource-id')})")
                    raise ValueError("Could not find Cancel button")

            elif "switch to text input mode" in action_type.lower():
                # For text input mode button
                print("Looking for text input mode button")
                mode_button = self.appium_handler.find_element(
                    AppiumBy.ID,
                    "com.google.android.deskclock:id/material_timepicker_mode_button"
                )
                if mode_button:
                    print("Found text input mode button")
                    mode_button.click()
                else:
                    # Print all visible buttons for debugging
                    all_buttons = self.appium_handler.find_elements(
                        AppiumBy.XPATH,
                        "//android.widget.Button"
                    )
                    print("Available buttons:")
                    for b in all_buttons:
                        print(f"- {b.get_attribute('text')} (id: {b.get_attribute('resource-id')})")
                    raise ValueError("Could not find text input mode button")

            # Add a small delay after each action
            time.sleep(1)

        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = str(e)

        return result

    def _verify_assertion(self, assertion: str) -> Dict[str, Any]:
        """Verifies a single assertion."""
        result = {
            "passed": True,
            "error": None
        }

        try:
            # Basic assertion checks
            if "is visible" in assertion.lower():
                # Check if element is visible
                element_desc = assertion.split("is visible")[0].strip()
                element = None
                
                # Try different locator strategies
                if element_desc.startswith("id:"):
                    element = self.appium_handler.find_element(AppiumBy.ID, element_desc[3:])
                elif element_desc.startswith("desc:"):
                    element = self.appium_handler.find_element(AppiumBy.ACCESSIBILITY_ID, element_desc[5:])
                else:
                    # Try all strategies
                    element = self.appium_handler.find_element(AppiumBy.ACCESSIBILITY_ID, element_desc)
                    if not element:
                        element = self.appium_handler.find_element(AppiumBy.XPATH, f"//*[@text='{element_desc}']")
                
                if not element or not element.is_displayed():
                    result["passed"] = False
                    result["error"] = f"Element '{element_desc}' is not visible"

            elif "contains text" in assertion.lower():
                # Check if element contains specific text
                parts = assertion.split("contains text")
                element_desc = parts[0].strip()
                expected_text = parts[1].strip().strip('"\'')
                
                element = None
                # Try different locator strategies
                if element_desc.startswith("id:"):
                    element = self.appium_handler.find_element(AppiumBy.ID, element_desc[3:])
                elif element_desc.startswith("desc:"):
                    element = self.appium_handler.find_element(AppiumBy.ACCESSIBILITY_ID, element_desc[5:])
                else:
                    # Try all strategies
                    element = self.appium_handler.find_element(AppiumBy.ACCESSIBILITY_ID, element_desc)
                    if not element:
                        element = self.appium_handler.find_element(AppiumBy.XPATH, f"//*[@text='{element_desc}']")
                
                if not element:
                    result["passed"] = False
                    result["error"] = f"Element '{element_desc}' not found"
                elif expected_text not in element.text:
                    result["passed"] = False
                    result["error"] = f"Element '{element_desc}' does not contain text '{expected_text}'"

            elif "is enabled" in assertion.lower():
                # Check if element is enabled
                element_desc = assertion.split("is enabled")[0].strip()
                element = None
                
                # Try different locator strategies
                if element_desc.startswith("id:"):
                    element = self.appium_handler.find_element(AppiumBy.ID, element_desc[3:])
                elif element_desc.startswith("desc:"):
                    element = self.appium_handler.find_element(AppiumBy.ACCESSIBILITY_ID, element_desc[5:])
                else:
                    # Try all strategies
                    element = self.appium_handler.find_element(AppiumBy.ACCESSIBILITY_ID, element_desc)
                    if not element:
                        element = self.appium_handler.find_element(AppiumBy.XPATH, f"//*[@text='{element_desc}']")
                
                if not element or not element.is_enabled():
                    result["passed"] = False
                    result["error"] = f"Element '{element_desc}' is not enabled"

            elif "is selected" in assertion.lower():
                # Check if element is selected
                element_desc = assertion.split("is selected")[0].strip()
                element = None
                
                # Try different locator strategies
                if element_desc.startswith("id:"):
                    element = self.appium_handler.find_element(AppiumBy.ID, element_desc[3:])
                elif element_desc.startswith("desc:"):
                    element = self.appium_handler.find_element(AppiumBy.ACCESSIBILITY_ID, element_desc[5:])
                else:
                    # Try all strategies
                    element = self.appium_handler.find_element(AppiumBy.ACCESSIBILITY_ID, element_desc)
                    if not element:
                        element = self.appium_handler.find_element(AppiumBy.XPATH, f"//*[@text='{element_desc}']")
                
                if not element or not element.is_selected():
                    result["passed"] = False
                    result["error"] = f"Element '{element_desc}' is not selected"

        except Exception as e:
            result["passed"] = False
            result["error"] = str(e)

        return result

    def run_tests(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Runs all test cases and returns the results."""
        print(f"\nStarting test execution for {len(test_cases)} test cases")
        
        for test_case in test_cases:
            result = self.execute_test_case(test_case)
            self.test_results.append(result)
            
            # Print test result
            print(f"\nTest Case {result['test_case_id']} - {result['title']}: {result['status']}")
            if result["status"] == "FAILED":
                print("Failures:")
                for failure in result["failures"]:
                    print(f"  - {failure}")

        return self.test_results

    def save_results(self, filename: str = "test_results.json"):
        """Saves test results to a JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            print(f"\nTest results saved to {filename}")
        except Exception as e:
            print(f"Error saving test results: {e}")

def main():
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

    # Initialize Appium handler
    handler = AppiumHandler(capabilities=CLOCK_CAPABILITIES)
    try:
        # Start the Appium driver
        handler.start_driver()
        print("Appium driver started successfully")

        # Initialize test runner
        runner = TestRunner(handler)
        print("Test runner initialized")

        # Load and run test cases
        test_cases = runner.load_test_cases()
        if not test_cases:
            print("No test cases found to execute")
            return

        print(f"\nLoaded {len(test_cases)} test cases")
        results = runner.run_tests(test_cases)

        # Save results
        runner.save_results()

        # Print summary
        passed = sum(1 for r in results if r["status"] == "PASSED")
        failed = sum(1 for r in results if r["status"] == "FAILED")
        print(f"\nTest Execution Summary:")
        print(f"Total Tests: {len(results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")

    except Exception as e:
        print(f"Error during test execution: {e}")
    finally:
        # Clean up
        handler.stop_driver()
        print("\nTest execution completed")

if __name__ == "__main__":
    main() 