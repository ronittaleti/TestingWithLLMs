# tests/test_sauce_labs.py
import pytest
import time
from utils.appium_handler import AppiumHandler, AppiumBy
from utils.ui_analyzer import UIChain

# Sauce Labs demo app capabilities
SAUCE_LABS_CAPABILITIES = {
    'platformName': 'Android',
    'automationName': 'UiAutomator2',
    'deviceName': 'test_emulator',  # Use your emulator name
    'appPackage': 'com.swaglabsmobileapp',
    'appActivity': 'com.swaglabsmobileapp.MainActivity',
    'noReset': True,
    'fullReset': False,
    'language': 'en',
    'locale': 'US'
}

# Pytest fixture to manage the Appium driver lifecycle for tests
@pytest.fixture(scope="module") # 'module' scope: driver starts once per module
def driver_handler():
    handler = AppiumHandler(capabilities=SAUCE_LABS_CAPABILITIES)
    try:
        handler.start_driver()
        yield handler # Provide the handler to the tests
    finally:
        handler.stop_driver()

# Pytest fixture to manage the UIChain instance
@pytest.fixture(scope="module")
def ui_chain():
    return UIChain()

# --- Test Cases ---

@pytest.mark.sauce_labs
def test_navigate_sauce_labs(driver_handler, ui_chain):
    """Tests navigating through the Sauce Labs demo app."""
    print("\n--- Starting Test: test_navigate_sauce_labs ---")
    
    # Set the driver in the rate limiter for keepalive
    ui_chain.rate_limiter.set_driver(driver_handler.driver)
    
    # Add a delay to ensure the app is fully loaded
    time.sleep(5)
    
    # Print the current screen state
    print("\nCurrent screen state:")
    print(f"Current activity: {driver_handler.driver.current_activity}")
    print(f"Current package: {driver_handler.driver.current_package}")
    
    goals = [
        "Enter username standard_user",
        "Enter password secret_sauce",
        "Click the login button",
        "Add the first item to cart",
        "Go to cart",
        "Checkout",
        "Enter first name John",
        "Enter last name Doe",
        "Enter zip code 12345",
        "Click continue",
        "Click finish"
    ]
    max_steps = 5

    for goal in goals:
        print(f"\n>>> Executing Goal: {goal} <<<")
        goal_achieved = False
        step = 0
        
        while step < max_steps and not goal_achieved:
            step += 1
            print(f"\nStep {step}/{max_steps} for goal '{goal}'")
            
            # Add a small delay between steps
            time.sleep(2)
            
            page_source = driver_handler.get_page_source()
            if not page_source:
                pytest.fail("Failed to get page source.")
                break

            elements = driver_handler.get_actionable_elements(page_source)
            print(f"\nFound {len(elements)} elements on screen")
            
            if not elements:
                print("Warning: No actionable elements found on screen.")
                continue

            # First, verify the current status of the goal
            achieved, reason = ui_chain.verify_goal_achievement(elements, goal)
            if achieved:
                print(f"Goal '{goal}' is already achieved: {reason}")
                goal_achieved = True
                break

            # If not achieved, get actions from the AI
            actions = ui_chain.choose_next_action(elements, goal)
            if not actions:
                print("No actions returned by AI")
                continue

            # Execute the first action
            action_type, by, value, input_text = actions[0]
            print(f"\nExecuting action: {action_type} on {value}")
            if input_text:
                print(f"Input text: {input_text}")

            success = False
            if action_type == "click":
                success = driver_handler.find_and_click(by, value)
            elif action_type == "type":
                element = driver_handler.find_element(by, value)
                if element:
                    element.clear()
                    element.send_keys(input_text)
                    success = True
                else:
                    success = False
            else:
                print(f"Unknown action type: {action_type}")
                success = False

            if not success:
                print(f"Failed to execute action: {action_type} on {value}")
                pytest.fail(f"Failed to execute action: {action_type} on {value}")
                break

            # After executing action, verify the new status
            achieved, reason = ui_chain.verify_goal_achievement(elements, goal)
            if achieved:
                print(f"Goal '{goal}' achieved: {reason}")
                goal_achieved = True
                break
            else:
                print(f"Goal status: {reason}")
                # If we've reached max steps and goal is not achieved, fail the test
                if step >= max_steps:
                    pytest.fail(f"Failed to achieve goal '{goal}' after {max_steps} steps: {reason}")

        if not goal_achieved:
            print(f"Failed to achieve goal: {goal}")
            pytest.fail(f"Failed to achieve goal: {goal}")

    print("\n--- Test Completed Successfully ---")  