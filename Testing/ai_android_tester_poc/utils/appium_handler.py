# utils/appium_handler.py
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
import time
import xml.etree.ElementTree as ET

# --- Configuration ---
# TODO: Adjust these capabilities based on your Appium server and device/emulator setup
APPIUM_SERVER_URL = 'http://localhost:4723'
APP_PACKAGE = 'com.swaglabsmobileapp'  # Sauce Labs demo app package
APP_ACTIVITY = 'com.swaglabsmobileapp.MainActivity'  # Sauce Labs demo app main activity

# Example capabilities (adjust as needed)
CAPABILITIES = {
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
# --- /Configuration ---

class AppiumHandler:
    """Handles Appium driver session and basic element interactions."""
    def __init__(self, server_url=APPIUM_SERVER_URL, capabilities=None):
        if not capabilities:
            raise ValueError("Capabilities must be provided when initializing AppiumHandler")
        self.server_url = server_url
        self.capabilities = capabilities
        self.driver = None

    def start_driver(self):
        """Starts the Appium driver session."""
        if self.driver is None:
            print("Starting Appium driver...")
            options = UiAutomator2Options().load_capabilities(self.capabilities)
            
            # Add session timeout prevention capabilities
            options.set_capability('newCommandTimeout', 0)  # No timeout for commands
            options.set_capability('commandTimeouts', {'command': 0})  # No timeout for any command
            options.set_capability('sessionOverride', True)  # Allow session override
            options.set_capability('autoGrantPermissions', True)  # Auto grant permissions
            options.set_capability('noReset', True)  # Don't reset app state
            options.set_capability('fullReset', False)  # Don't do full reset
            
            try:
                self.driver = webdriver.Remote(self.server_url, options=options)
                self.driver.implicitly_wait(5) # Wait implicitly for elements
                
                # Add a delay to ensure the app is launched
                time.sleep(5)
                
                # Verify we're in the correct app
                current_package = self.driver.current_package
                current_activity = self.driver.current_activity
                print(f"Current package: {current_package}")
                print(f"Current activity: {current_activity}")
                
                if current_package != self.capabilities['appPackage']:
                    print(f"Not in the {self.capabilities['appPackage']} app, attempting to launch it...")
                    self.driver.activate_app(self.capabilities['appPackage'])
                    time.sleep(3)  # Wait for app to launch
                    
                    # Verify again
                    current_package = self.driver.current_package
                    current_activity = self.driver.current_activity
                    print(f"After launch - Current package: {current_package}")
                    print(f"After launch - Current activity: {current_activity}")
                
                print("Appium driver started successfully.")
            except Exception as e:
                print(f"Error starting Appium driver: {e}")
                self.driver = None
                raise

    def stop_driver(self):
        """Stops the Appium driver session."""
        if self.driver:
            print("Stopping Appium driver...")
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error stopping Appium driver: {e}")
            finally:
                self.driver = None
                print("Appium driver stopped.")

    def get_page_source(self):
        """Gets the XML page source of the current screen."""
        if not self.driver:
            print("Driver not started.")
            return None
        try:
            source = self.driver.page_source
            print(f"Page source length: {len(source)}")
            print("Current activity:", self.driver.current_activity)
            return source
        except Exception as e:
            print(f"Error getting page source: {e}")
            if "InvalidSessionIdException" in str(e):
                print("Session invalid, attempting to restart driver...")
                self.stop_driver()
                self.start_driver()
            return None

    def find_element(self, by, value, max_scroll_attempts=5):
        """Finds a single element, scrolling if necessary."""
        if not self.driver:
            print("Driver not started.")
            return None
        
        # First try to find the element without scrolling
        try:
            element = self.driver.find_element(by=by, value=value)
            if element and element.is_displayed():
                print("Element found immediately")
                return element
        except Exception as e:
            print(f"Element not immediately visible: {e}")
        
        # If element not found, start scrolling and collecting elements
        found_elements = []
        window_size = self.driver.get_window_size()
        screen_width = window_size['width']
        screen_height = window_size['height']
        
        # Calculate scroll parameters
        start_x = screen_width // 2
        start_y = int(screen_height * 0.8)  # Start from 80% down
        end_x = screen_width // 2
        end_y = int(screen_height * 0.2)  # End at 20% down
        
        # First pass: collect all elements
        for attempt in range(max_scroll_attempts):
            print(f"\nScroll attempt {attempt + 1}/{max_scroll_attempts}")
            
            # Perform the scroll
            self.driver.swipe(start_x, start_y, end_x, end_y, 1000)
            time.sleep(1)  # Wait for scroll to complete
            
            # Get all elements on the current screen
            try:
                # Try to find the element directly first
                element = self.driver.find_element(by=by, value=value)
                if element and element.is_displayed():
                    print("Element found after scrolling")
                    return element
                
                # If not found, collect all elements for analysis
                elements = self.driver.find_elements(by=AppiumBy.XPATH, value="//*")
                print(f"Found {len(elements)} elements on screen")
                
                # Collect element information
                for elem in elements:
                    try:
                        # Get element attributes
                        text = elem.text
                        content_desc = elem.get_attribute('content-desc')
                        resource_id = elem.get_attribute('resource-id')
                        class_name = elem.get_attribute('class')
                        
                        # Only store elements with useful identifiers
                        if text or content_desc or resource_id:
                            found_elements.append({
                                'element': elem,
                                'text': text,
                                'content_desc': content_desc,
                                'resource_id': resource_id,
                                'class_name': class_name
                            })
                            
                    except Exception as e:
                        print(f"Error analyzing element: {e}")
                        continue
                
            except Exception as e:
                print(f"Error during scroll attempt {attempt + 1}: {e}")
                continue
        
        # After collecting all elements, analyze them to find the best match
        print(f"\nAnalyzing {len(found_elements)} collected elements...")
        
        # First try exact matches
        for elem_info in found_elements:
            if by == AppiumBy.ACCESSIBILITY_ID and elem_info['content_desc'] == value:
                print("Found exact match by accessibility ID")
                return elem_info['element']
            elif by == AppiumBy.ID and elem_info['resource_id'] == value:
                print("Found exact match by ID")
                return elem_info['element']
            elif by == AppiumBy.XPATH and value in str(elem_info['element'].get_attribute('xpath')):
                print("Found exact match by XPath")
                return elem_info['element']
            elif by == AppiumBy.CLASS_NAME and elem_info['class_name'] == value:
                print("Found exact match by class name")
                return elem_info['element']
        
        # If no exact match, try partial matches
        best_match = None
        best_score = 0
        
        for elem_info in found_elements:
            score = 0
            
            # Score based on various attributes
            if elem_info['text'] and value.lower() in elem_info['text'].lower():
                score += 2
            if elem_info['content_desc'] and value.lower() in elem_info['content_desc'].lower():
                score += 3
            if elem_info['resource_id'] and value.lower() in elem_info['resource_id'].lower():
                score += 4
            
            # If this is a better match than our current best, update
            if score > best_score:
                best_score = score
                best_match = elem_info['element']
                print(f"New best match with score {score}:")
                print(f"Text: {elem_info['text']}")
                print(f"Content Description: {elem_info['content_desc']}")
                print(f"Resource ID: {elem_info['resource_id']}")
        
        if best_match:
            print(f"Found best matching element with score {best_score}")
            return best_match
        
        print("No matching element found after all scroll attempts")
        return None

    def find_elements(self, by, value):
        """Finds multiple elements."""
        if not self.driver:
            print("Driver not started.")
            return []
        try:
            return self.driver.find_elements(by=by, value=value)
        except Exception as e:
            print(f"Error finding elements using {by}='{value}': {e}")
            if "InvalidSessionIdException" in str(e):
                print("Session invalid, attempting to restart driver...")
                self.stop_driver()
                self.start_driver()
            return []

    def scroll_to_element(self, element):
        """Scrolls the screen to make an element visible."""
        if not self.driver or not element:
            print("Driver not started or element is None.")
            return False
        
        try:
            # First check if the element is already visible
            if element.is_displayed():
                print("Element is already visible")
                return True
            
            # Try to get the element's text or content description
            try:
                text = element.text
                if text:
                    selector = f'text("{text}")'
                else:
                    content_desc = element.get_attribute('content-desc')
                    if content_desc:
                        selector = f'description("{content_desc}")'
                    else:
                        print("Element has no text or content description")
                        return False
                
                # Create the UiAutomator scroll command
                scroll_command = f'new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().{selector})'
                print(f"Using UiAutomator scroll command: {scroll_command}")
                
                # Execute the scroll command
                self.driver.find_element(by=AppiumBy.ANDROID_UIAUTOMATOR, value=scroll_command)
                time.sleep(1)  # Wait for scroll to complete
                
                if element.is_displayed():
                    print("Element is now visible")
                    return True
                
                print("Element still not visible after scrolling")
                return False
                
            except Exception as e:
                print(f"Error getting element attributes: {e}")
                return False
            
        except Exception as e:
            print(f"Error scrolling to element: {e}")
            print(f"Error type: {type(e)}")
            return False

    def click_element(self, element):
        """Clicks a given element, scrolling to it first if needed."""
        if not self.driver or not element:
            print("Driver not started or element is None.")
            return False
        try:
            # First try to scroll to the element
            self.scroll_to_element(element)
            
            # Now try to click
            element.click()
            time.sleep(1)  # Add a small delay after clicks for UI to settle
            return True
        except Exception as e:
            print(f"Error clicking element: {e}")
            if "InvalidSessionIdException" in str(e):
                print("Session invalid, attempting to restart driver...")
                self.stop_driver()
                self.start_driver()
            return False

    def find_and_click(self, by, value):
        """Finds an element and clicks it."""
        element = self.find_element(by, value)
        if element:
            return self.click_element(element)
        else:
            print(f"Element not found for clicking: {by}='{value}'")
            return False

    def get_actionable_elements(self, page_source):
        """
        Parses the XML page source and extracts potentially actionable elements.
        Returns a list of dictionaries, each representing an element.
        """
        elements = []
        if not page_source:
            print("No page source provided")
            return elements

        try:
            print("\n--- Starting XML Parsing ---")
            root = ET.fromstring(page_source)
            print(f"Root element: {root.tag}")
            
            # Find ALL elements that could be actionable, regardless of visibility
            all_elements = root.findall('.//*')
            print(f"\nTotal elements found in XML: {len(all_elements)}")
            
            # Find all potentially actionable elements
            clickable_elements = root.findall('.//*[@clickable="true"]')
            print(f"Clickable elements: {len(clickable_elements)}")
            
            content_desc_elements = root.findall('.//*[@content-desc]')
            print(f"Elements with content-desc: {len(content_desc_elements)}")
            
            button_elements = root.findall('.//android.widget.Button')
            print(f"Button elements: {len(button_elements)}")
            
            textview_elements = root.findall('.//android.widget.TextView')
            print(f"TextView elements: {len(textview_elements)}")
            
            imagebutton_elements = root.findall('.//android.widget.ImageButton')
            print(f"ImageButton elements: {len(imagebutton_elements)}")
            
            edittext_elements = root.findall('.//android.widget.EditText')
            print(f"EditText elements: {len(edittext_elements)}")

            # Print details of the first few elements of each type
            print("\nSample elements found:")
            for elem_type, elem_list in [
                ("Clickable", clickable_elements[:3]),
                ("Content-desc", content_desc_elements[:3]),
                ("Button", button_elements[:3]),
                ("TextView", textview_elements[:3]),
                ("ImageButton", imagebutton_elements[:3]),
                ("EditText", edittext_elements[:3])
            ]:
                print(f"\nFirst 3 {elem_type} elements:")
                for elem in elem_list:
                    print(f"  - {elem.tag}: {elem.attrib}")

            # Combine all found elements into a single list
            all_actionable_elements = (
                clickable_elements +
                content_desc_elements +
                button_elements +
                textview_elements +
                imagebutton_elements +
                edittext_elements
            )
            
            # Remove duplicates by converting to a set and back to a list
            unique_elements = list(set(all_actionable_elements))
            print(f"\nTotal unique potentially actionable elements: {len(unique_elements)}")

            # Process each unique element
            for elem in unique_elements:
                attrs = elem.attrib
                element_info = {
                    'class': attrs.get('class'),
                    'text': attrs.get('text'),
                    'content-desc': attrs.get('content-desc'),
                    'resource-id': attrs.get('resource-id'),
                    'clickable': attrs.get('clickable') == 'true',
                    'bounds': attrs.get('bounds'),
                    'enabled': attrs.get('enabled') == 'true',
                    'focusable': attrs.get('focusable') == 'true',
                    'long-clickable': attrs.get('long-clickable') == 'true',
                    'package': attrs.get('package'),
                    'checkable': attrs.get('checkable') == 'true',
                    'checked': attrs.get('checked') == 'true',
                    'scrollable': attrs.get('scrollable') == 'true',
                    'selected': attrs.get('selected') == 'true',
                    'visible': attrs.get('visible') == 'true'  # Add visibility flag
                }
                
                # Only add elements that are either clickable or have a non-empty content description
                if element_info['clickable'] or (element_info['content-desc'] and element_info['content-desc'].strip()):
                    print(f"\nAdding actionable element: {element_info}")
                    elements.append(element_info)

            print(f"\nTotal actionable elements found: {len(elements)}")

        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            print(f"First 100 characters of page source: {page_source[:100]}")
        except Exception as e:
            print(f"An unexpected error occurred during XML parsing: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")

        return elements

# Example usage (for testing the handler itself)
if __name__ == '__main__':
    handler = AppiumHandler()
    try:
        driver = handler.start_driver()
        if driver:
            print("Getting page source...")
            source = handler.get_page_source()
            if source:
                print(f"Page source length: {len(source)}")
            # Example: Try to find the "Alarm" tab (content description)
            alarm_tab = handler.find_element(AppiumBy.ACCESSIBILITY_ID, "Alarm")
            if alarm_tab:
                print("Found 'Alarm' tab.")
                # handler.click_element(alarm_tab) # Uncomment to test clicking
            else:
                print("'Alarm' tab not found by accessibility ID.")

            # Example: Find by text (less reliable, depends on exact text)
            # clock_element = handler.find_element(AppiumBy.XPATH, "//*[@text='Clock']")
            # if clock_element:
            #     print("Found element with text 'Clock'.")

    finally:
        handler.stop_driver()

def test_navigate_tabs(driver_handler):
    """Tests navigating between the main tabs of the Clock app."""
    print("\n--- Starting Test: test_navigate_tabs ---")
    
    # Add a delay to ensure the app is fully loaded
    time.sleep(5)
    
    # Print the current screen state
    print("\nCurrent screen state:")
    print(f"Current activity: {driver_handler.driver.current_activity}")
    print(f"Current package: {driver_handler.driver.current_package}")
    
    goals = [
        "Go to Alarm",
        "Go to Clock",
        "Go to Timer",
        "Go to Stopwatch",
        "Go back to Alarm"
    ]
    max_steps = 5

    for goal in goals:
        print(f"\n>>> Executing Goal: {goal} <<<")
        goal_achieved = False
        for step in range(max_steps):
            print(f"\nStep {step + 1}/{max_steps} for goal '{goal}'")
            
            # Add a small delay between steps
            time.sleep(2)
            
            page_source = driver_handler.get_page_source()
            if not page_source:
                pytest.fail("Failed to get page source.")
                break

            elements = get_actionable_elements(page_source)
            print(f"\nFound {len(elements)} elements on screen")
            
            if not elements:
                print("Warning: No actionable elements found on screen.")
                # Try to find elements by different methods
                print("\nTrying alternative element finding methods:")
                # Try finding by accessibility ID
                alarm_tab = driver_handler.find_element(AppiumBy.ACCESSIBILITY_ID, "Alarm")
                if alarm_tab:
                    print("Found 'Alarm' tab by accessibility ID")
                # Try finding by text
                clock_tab = driver_handler.find_element(AppiumBy.XPATH, "//*[@text='Clock']")
                if clock_tab:
                    print("Found 'Clock' tab by text")
                continue

            # Rest of the test code... 