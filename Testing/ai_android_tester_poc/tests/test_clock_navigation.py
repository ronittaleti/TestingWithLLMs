# tests/test_clock_navigation.py
import pytest
import time
from utils.appium_handler import AppiumHandler, AppiumBy
from utils.ui_analyzer import UIChain

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

# Pytest fixture to manage the Appium driver lifecycle for tests
@pytest.fixture(scope="module") # 'module' scope: driver starts once per module
def driver_handler():
    handler = AppiumHandler(capabilities=CLOCK_CAPABILITIES)
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

def test_navigate_tabs(driver_handler, ui_chain):
    """Tests navigating between the main tabs of the Clock app."""
    print("\n--- Starting Test: test_navigate_tabs ---")
    goals = [
        "Go to Alarm",
        "Go to Clock",
        "Go to Timer",
        "Go to Stopwatch",
        "Go back to Alarm" # Loop back
    ]
    max_steps = 5 # Safety break per goal

    for goal in goals:
        print(f"\n>>> Executing Goal: {goal} <<<")
        goal_achieved = False
        for step in range(max_steps):
            print(f"\nStep {step + 1}/{max_steps} for goal '{goal}'")
            page_source = driver_handler.get_page_source()
            if not page_source:
                pytest.fail("Failed to get page source.")
                break

            elements = driver_handler.get_actionable_elements(page_source)
            if not elements:
                 print("Warning: No actionable elements found on screen.")
                 # Maybe wait a bit more? Or fail? For now, continue.
                 time.sleep(1)
                 continue

            # --- AI Agent determines action ---
            action = ui_chain.choose_next_action(elements, goal)
            # --- /AI Agent ---

            if not action:
                print("AI could not determine an action. Moving to next goal or failing.")
                # Depending on strictness, you might fail here:
                # pytest.fail(f"AI failed to find action for goal: {goal}")
                break # Move to next goal in this PoC

            action_type, by, value = action

            # --- Executor performs action ---
            print(f"Executor: Attempting to {action_type} element identified by {by}='{value}'")
            if action_type == 'click':
                clicked = driver_handler.find_and_click(by, value)
                if not clicked:
                    print(f"Executor: Failed to click element {by}='{value}'.")
                    # Optional: Add retry logic or fail the test
                    # For PoC, we might continue and see if it resolves
                    time.sleep(2) # Wait longer if click failed
                    continue
                else:
                     print(f"Executor: Click successful.")
                     # Very basic goal check: Did clicking the target element work?
                     # A real check would verify the *state* after the click.
                     goal_achieved = True
                     break # Assume click achieved the navigation goal for this PoC step
            else:
                 print(f"Executor: Action type '{action_type}' not implemented in this PoC.")
                 break
            # --- /Executor ---

            # Add a small delay to allow UI to transition
            time.sleep(1)

        if not goal_achieved:
             pytest.fail(f"Failed to achieve goal '{goal}' within {max_steps} steps.")

    print("\n--- Test Finished: test_navigate_tabs ---")

# Example of a more complex flow (requires refining the AI simulation)
# def test_set_alarm(driver_handler):
#     print("\n--- Starting Test: test_set_alarm ---")
#     # TODO: Implement sequence: Navigate to Alarm -> Click Add -> Set Time -> Save
#     # This would require more sophisticated UI parsing and action simulation
#     # (e.g., handling time pickers, finding 'Save' buttons)
#     pytest.skip("Test not implemented yet")
#     pass 