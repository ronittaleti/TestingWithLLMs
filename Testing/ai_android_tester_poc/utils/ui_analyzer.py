# utils/ui_analyzer.py
from appium.webdriver.common.appiumby import AppiumBy
import xml.etree.ElementTree as ET
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
import os
from dotenv import load_dotenv
import time
from threading import Lock
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Get rate limit from .env
RATE_LIMIT = int(os.getenv('RATE_LIMIT', 60))  # Default to 60 if not set
MODEL_NAME = os.getenv('MODEL_NAME', 'gemini-1.5-pro')
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.7))

# Configure Gemini
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# List available models
print("\nListing available models:")
try:
    models = genai.list_models()
    for model in models:
        print(f"- {model.name}")
        print(f"  Supported methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")

# Rate limiting setup
class RateLimiter:
    def __init__(self, requests_per_minute):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.lock = Lock()
        self.retry_count = 0
        self.max_retries = 3
        self.driver = None  # Will be set when needed
    
    def set_driver(self, driver):
        """Set the driver for keepalive pings."""
        self.driver = driver
    
    def _send_keepalive(self):
        """Send a keepalive command to maintain the session."""
        if self.driver:
            try:
                # Get current activity - a lightweight operation
                self.driver.current_activity
            except:
                pass  # Ignore any errors during keepalive
    
    def wait_if_needed(self):
        with self.lock:
            now = datetime.now()
            # Remove requests older than 1 minute
            self.requests = [req for req in self.requests if now - req < timedelta(minutes=1)]
            
            if len(self.requests) >= self.requests_per_minute:
                # Wait until the oldest request is 1 minute old
                wait_time = (self.requests[0] + timedelta(minutes=1) - now).total_seconds()
                if wait_time > 0:
                    print(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    # Send keepalive every 10 seconds
                    while wait_time > 0:
                        time.sleep(min(10, wait_time))
                        wait_time -= 10
                        self._send_keepalive()
                    self.requests = self.requests[1:]
            
            self.requests.append(now)
    
    def handle_rate_limit_error(self, error_message):
        """Handle rate limit errors with exponential backoff."""
        if "429" in error_message and self.retry_count < self.max_retries:
            self.retry_count += 1
            wait_time = 2 ** self.retry_count  # Exponential backoff: 2, 4, 8 seconds
            print(f"Rate limit error. Retry {self.retry_count}/{self.max_retries}. Waiting {wait_time} seconds...")
            # Send keepalive every 10 seconds
            while wait_time > 0:
                time.sleep(min(10, wait_time))
                wait_time -= 10
                self._send_keepalive()
            return True
        return False

# Initialize rate limiter with a more conservative limit
rate_limiter = RateLimiter(requests_per_minute=1)  # Only 1 request per minute

# Initialize the model
model = genai.GenerativeModel(MODEL_NAME)

# Configure LangChain with Google Generative AI
llm = GoogleGenerativeAI(
    model=MODEL_NAME,
    google_api_key=os.getenv('GOOGLE_API_KEY'),
    temperature=TEMPERATURE,
    convert_system_message_to_human=True
)

def get_actionable_elements(page_source):
    """
    Parses the XML page source and extracts potentially actionable elements.
    Returns a list of dictionaries, each representing an element.
    Simplified for PoC. A real version would be more robust.
    """
    elements = []
    if not page_source:
        return elements

    try:
        root = ET.fromstring(page_source)
        # Find elements that are typically clickable/actionable
        for elem in root.findall('.//*[@clickable="true"], .//*[@content-desc], .//android.widget.Button'):
            attrs = elem.attrib
            element_info = {
                'class': attrs.get('class'),
                'text': attrs.get('text'),
                'content-desc': attrs.get('content-desc'),
                'resource-id': attrs.get('resource-id'),
                'clickable': attrs.get('clickable') == 'true',
                # Add bounds if needed for coordinate-based clicks
                'bounds': attrs.get('bounds'),
                # Reference to the XML element itself (optional, for advanced parsing)
                # 'xml_element': elem
            }
            # Filter out elements without useful identifiers (text or content-desc)
            if element_info['text'] or element_info['content-desc']:
                 elements.append(element_info)

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during XML parsing: {e}")


    # Basic deduplication based on text/content-desc
    unique_elements = []
    seen_identifiers = set()
    for elem in elements:
        identifier = elem['content-desc'] or elem['text']
        if identifier and identifier not in seen_identifiers:
            unique_elements.append(elem)
            seen_identifiers.add(identifier)

    return unique_elements

def format_elements_for_llm(elements):
    """Formats the UI elements into a natural language description for the LLM."""
    element_descriptions = []
    for elem in elements:
        desc = []
        if elem.get('text'):
            desc.append(f"text: '{elem['text']}'")
        if elem.get('content-desc'):
            desc.append(f"description: '{elem['content-desc']}'")
        if elem.get('class'):
            desc.append(f"type: {elem['class']}")
        if elem.get('clickable') == 'true':
            desc.append("clickable")
        if desc:
            element_descriptions.append(" - " + ", ".join(desc))
    
    return "\n".join(element_descriptions)

class UIChain:
    def __init__(self):
        # Create prompt templates for different AI tasks
        self.action_prompt = PromptTemplate(
            input_variables=["goal", "elements", "history", "current_state"],
            template="""
            You are an AI assistant helping to test an Android app. Your goal is to help navigate the app to achieve a specific goal.
            
            Previous actions taken:
            {history}
            
            Current state of the app:
            {current_state}
            
            Current goal: {goal}
            
            Available UI elements:
            {elements}
            
            Please analyze the available UI elements and determine what action(s) are needed to achieve the goal.
            
            For text input goals (like "Enter username standard_user"):
            1. Look for input fields (EditText elements) that match the field name
            2. Check the resource-id, text, and content-desc of each element
            3. For username/password fields, look for elements with:
               - resource-id containing "username" or "user-name"
               - text containing "Username" or "User Name"
               - content-desc containing "username" or "user name"
            4. The action should be "type" with the exact text to enter
            5. Use the most reliable identifier (preferably resource-id)
            
            For button click goals:
            1. Look for buttons that match the goal description
            2. Use the most reliable identifier (preferably resource-id or content-desc)
            3. The action should be "click"
            4. The element will be automatically scrolled into view if needed
            
            For navigation goals:
            1. Look for navigation elements (tabs, menu items, etc.)
            2. Use the most reliable identifier
            3. The action should be "click"
            4. The element will be automatically scrolled into view if needed
            
            Your response should be a JSON object with the following structure:
            {{
                "actions": [
                    {{
                        "action_type": "click",  // The type of action to take (click, type)
                        "by": "accessibility_id",  // How to find the element (accessibility_id, xpath, etc.)
                        "value": "element_value",  // The value to use to find the element
                        "input": "text_to_type"  // Optional: text to type if action_type is "type"
                    }},
                    // ... more actions if needed
                ],
                "reasoning": "explanation of why these actions were chosen",
                "confidence": 0.95,  // Confidence score between 0 and 1
                "state_update": "description of how the app state will change after these actions"
            }}
            
            Only respond with the JSON object, nothing else. Do not include any markdown formatting or code block markers.
            """
        )
        
        self.verification_prompt = PromptTemplate(
            input_variables=["goal", "elements", "history", "current_state"],
            template="""
            You are an AI assistant helping to test an Android app. Your task is to verify if a specific goal has been achieved.
            
            Previous actions taken:
            {history}
            
            Current state of the app:
            {current_state}
            
            Goal to verify: {goal}
            
            Available UI elements:
            {elements}
            
            Please analyze the available UI elements and determine the status of the goal.
            
            For text input goals (like "Enter username standard_user"):
            1. Look for input fields (EditText elements) that match the field name
            2. Check if the field's current text matches the expected value
            3. If the text matches exactly, the goal is ACHIEVED
            4. If the field exists but has different text, the goal is NOT YET MET
            5. If the field doesn't exist or is not accessible, the goal is FAILED
            
            For button click goals:
            1. Look for the button in the current UI
            2. If the button is not visible and we're on the expected next screen, the goal is ACHIEVED
            3. If the button is still visible and we're on the same screen, the goal is NOT YET MET
            4. If we're on an unexpected screen, the goal is FAILED
            
            For navigation goals:
            1. Check if we're on the expected screen
            2. If we're on the target screen with expected elements, the goal is ACHIEVED
            3. If we're on the current screen but haven't reached the target, the goal is NOT YET MET
            4. If we're on an unexpected screen, the goal is FAILED
            
            Your response should be a JSON object with the following structure:
            {{
                "status": "ACHIEVED|FAILED|NOT_YET_MET",  // The current status of the goal
                "reason": "explanation of the current status",
                "confidence": 0.95,  // Confidence score between 0 and 1
                "next_action_needed": true/false,  // Whether another action is needed
                "details": "additional details about the verification process"
            }}
            
            Only respond with the JSON object, nothing else.
            """
        )
        
        # Initialize memory as a list
        self.memory = []
        self.current_state = "App launched"
        
        # Create the chains
        self.action_chain = LLMChain(
            llm=llm,
            prompt=self.action_prompt,
            verbose=True
        )
        
        self.verification_chain = LLMChain(
            llm=llm,
            prompt=self.verification_prompt,
            verbose=True
        )
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(requests_per_minute=60)  # 60 requests per minute (1 per second)
    
    def choose_next_action(self, elements, goal):
        """
        Uses Gemini to choose the next action(s) based on available elements and goal.
        Returns a list of tuples: [(action_type, by, value, input), ...]
        """
        print("\n--- AI Action Selection ---")
        print(f"Goal: {goal}")
        print(f"Current state: {self.current_state}")
        
        # Format the elements for the LLM
        elements_description = format_elements_for_llm(elements)
        print(f"\nAvailable UI elements:\n{elements_description}")
        
        try:
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            
            # Format history as a string
            history_str = "\n".join(self.memory) if self.memory else "No previous actions taken."
            
            # Create the prompt
            prompt = f"""
            You are an AI assistant helping to test an Android app. Your goal is to help navigate the app to achieve a specific goal.
            
            Previous actions taken:
            {history_str}
            
            Current state of the app:
            {self.current_state}
            
            Current goal: {goal}
            
            Available UI elements:
            {elements_description}
            
            Please analyze the available UI elements and determine what action(s) are needed to achieve the goal.
            
            For text input goals (like "Enter username standard_user"):
            1. Look for input fields (EditText elements) that match the field name
            2. Check the resource-id, text, and content-desc of each element
            3. For username/password fields, look for elements with:
               - resource-id containing "username" or "user-name"
               - text containing "Username" or "User Name"
               - content-desc containing "username" or "user name"
            4. The action should be "type" with the exact text to enter
            5. Use the most reliable identifier (preferably resource-id)
            
            For button click goals:
            1. Look for buttons that match the goal description
            2. Use the most reliable identifier (preferably resource-id or content-desc)
            3. The action should be "click"
            4. The element will be automatically scrolled into view if needed
            
            For navigation goals:
            1. Look for navigation elements (tabs, menu items, etc.)
            2. Use the most reliable identifier
            3. The action should be "click"
            4. The element will be automatically scrolled into view if needed
            
            Your response should be a JSON object with the following structure:
            {{
                "actions": [
                    {{
                        "action_type": "click",  // The type of action to take (click, type)
                        "by": "accessibility_id",  // How to find the element (accessibility_id, xpath, etc.)
                        "value": "element_value",  // The value to use to find the element
                        "input": "text_to_type"  // Optional: text to type if action_type is "type"
                    }},
                    // ... more actions if needed
                ],
                "reasoning": "explanation of why these actions were chosen",
                "confidence": 0.95,  // Confidence score between 0 and 1
                "state_update": "description of how the app state will change after these actions"
            }}
            
            Only respond with the JSON object, nothing else. Do not include any markdown formatting or code block markers.
            """
            
            # Get response from Gemini with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(prompt)
                    response_text = response.text.strip()
                    
                    # Clean up the response by removing markdown code block markers if present
                    if response_text.startswith('```json'):
                        response_text = response_text[7:]  # Remove ```json
                    if response_text.startswith('```'):
                        response_text = response_text[3:]  # Remove ```
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]  # Remove ```
                    
                    response_text = response_text.strip()
                    print(f"\nAI response: {response_text}")
                    
                    # Parse the JSON response
                    action_data = json.loads(response_text)
                    
                    # Update state based on the AI's prediction
                    self.current_state = action_data.get('state_update', self.current_state)
                    
                    # Convert the actions to the appropriate format
                    actions = []
                    for action in action_data['actions']:
                        # Convert the 'by' string to the appropriate AppiumBy value
                        by_map = {
                            'accessibility_id': AppiumBy.ACCESSIBILITY_ID,
                            'xpath': AppiumBy.XPATH,
                            'id': AppiumBy.ID,
                            'class_name': AppiumBy.CLASS_NAME,
                            'description': AppiumBy.ACCESSIBILITY_ID  # Map 'description' to accessibility_id
                        }
                        
                        by_value = by_map.get(action['by'].lower())
                        if not by_value:
                            print(f"Warning: Unknown 'by' value: {action['by']}")
                            continue
                        
                        # Add the action to memory
                        action_desc = f"Action: {action['action_type']} on {action['value']}"
                        if action.get('input'):
                            action_desc += f" with input '{action['input']}'"
                        self.memory.append(action_desc)
                        
                        # Add the action to the list
                        actions.append((
                            action['action_type'],
                            by_value,
                            action['value'],
                            action.get('input', None)
                        ))
                    
                    print(f"AI Decision: {action_data['reasoning']}")
                    print(f"Confidence: {action_data['confidence']}")
                    print(f"New state: {self.current_state}")
                    
                    return actions
                    
                except Exception as e:
                    error_message = str(e)
                    print(f"Attempt {attempt + 1}/{max_retries} failed: {error_message}")
                    
                    if "429" in error_message:
                        if self.rate_limiter.handle_rate_limit_error(error_message):
                            continue
                    
                    if attempt == max_retries - 1:  # Last attempt
                        print("Max retries reached. Falling back to simulated action.")
                        return choose_next_action_simulated(elements, goal)
                    else:
                        time.sleep(2 ** attempt)  # Exponential backoff
            
        except Exception as e:
            print(f"Error getting AI decision: {e}")
            return choose_next_action_simulated(elements, goal)  # Fallback to simulated action
    
    def verify_goal_achievement(self, elements, goal):
        """
        Uses Gemini to verify if a goal has been achieved based on the current UI state.
        Returns a tuple: (achieved, reason)
        """
        print("\n--- AI Goal Verification ---")
        print(f"Verifying goal: {goal}")
        print(f"Current state: {self.current_state}")
        
        # Format the elements for the LLM
        elements_description = format_elements_for_llm(elements)
        print(f"\nAvailable UI elements:\n{elements_description}")
        
        try:
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            
            # Format history as a string
            history_str = "\n".join(self.memory) if self.memory else "No previous actions taken."
            
            # Create the prompt
            prompt = f"""
            You are an AI assistant helping to test an Android app. Your task is to verify if a specific goal has been achieved.
            
            Previous actions taken:
            {history_str}
            
            Current state of the app:
            {self.current_state}
            
            Goal to verify: {goal}
            
            Available UI elements:
            {elements_description}
            
            Please analyze the available UI elements and determine the status of the goal.
            
            For text input goals (like "Enter username standard_user"):
            1. Look for input fields (EditText elements) that match the field name
            2. Check if the field's current text matches the expected value
            3. If the text matches exactly, the goal is ACHIEVED
            4. If the field exists but has different text, the goal is NOT YET MET
            5. If the field doesn't exist or is not accessible, the goal is FAILED
            
            For button click goals:
            1. Look for the button in the current UI
            2. If the button is not visible and we're on the expected next screen, the goal is ACHIEVED
            3. If the button is still visible and we're on the same screen, the goal is NOT YET MET
            4. If we're on an unexpected screen, the goal is FAILED
            
            For navigation goals:
            1. Check if we're on the expected screen
            2. If we're on the target screen with expected elements, the goal is ACHIEVED
            3. If we're on the current screen but haven't reached the target, the goal is NOT YET MET
            4. If we're on an unexpected screen, the goal is FAILED
            
            Your response should be a JSON object with the following structure:
            {{
                "status": "ACHIEVED|FAILED|NOT_YET_MET",  // The current status of the goal
                "reason": "explanation of the current status",
                "confidence": 0.95,  // Confidence score between 0 and 1
                "next_action_needed": true/false,  // Whether another action is needed
                "details": "additional details about the verification process"
            }}
            
            Only respond with the JSON object, nothing else.
            """
            
            # Get response from Gemini with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(prompt)
                    response_text = response.text.strip()
                    
                    # Clean up the response by removing markdown code block markers if present
                    if response_text.startswith('```json'):
                        response_text = response_text[7:]  # Remove ```json
                    if response_text.startswith('```'):
                        response_text = response_text[3:]  # Remove ```
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]  # Remove ```
                    
                    response_text = response_text.strip()
                    print(f"\nAI response: {response_text}")
                    
                    # Parse the JSON response
                    verification_data = json.loads(response_text)
                    
                    print(f"Verification Result: {verification_data['reason']}")
                    print(f"Confidence: {verification_data['confidence']}")
                    print(f"Details: {verification_data['details']}")
                    
                    return (
                        verification_data['status'] == "ACHIEVED",
                        verification_data['reason']
                    )
                    
                except Exception as e:
                    error_message = str(e)
                    print(f"Attempt {attempt + 1}/{max_retries} failed: {error_message}")
                    
                    if "429" in error_message:
                        if self.rate_limiter.handle_rate_limit_error(error_message):
                            continue
                    
                    if attempt == max_retries - 1:  # Last attempt
                        print("Max retries reached. Assuming goal not achieved.")
                        return False, "Verification failed after max retries"
                    else:
                        time.sleep(2 ** attempt)  # Exponential backoff
            
        except Exception as e:
            print(f"Error verifying goal achievement: {e}")
            return False, f"Error during verification: {str(e)}"

# Keep the simulated version for testing/fallback
def choose_next_action_simulated(elements, goal):
    """
    Simulates an AI agent choosing the next action based on available elements and goal.
    This is a simplified version for testing purposes.
    """
    print("\n--- AI Simulation ---")
    print(f"Goal: {goal}")
    
    # Extract text and content descriptions from elements
    available_elements = []
    for elem in elements:
        text = elem.get('text', '')
        content_desc = elem.get('content-desc', '')
        if text:
            available_elements.append(text)
        if content_desc:
            available_elements.append(content_desc)
    
    print(f"Available elements: {available_elements}")
    
    # Simple goal matching
    if "Alarm" in goal:
        # Look for Alarm tab or button
        for elem in elements:
            text = elem.get('text', '')
            content_desc = elem.get('content-desc', '')
            if (text and text == 'Alarm') or (content_desc and content_desc == 'Alarm') or \
               (text and 'Alarm' in text) or (content_desc and 'Alarm' in content_desc):
                return ('click', AppiumBy.ACCESSIBILITY_ID, 'Alarm')
    elif "Clock" in goal:
        # Look for Clock tab or button
        for elem in elements:
            text = elem.get('text', '')
            content_desc = elem.get('content-desc', '')
            if (text and text == 'Clock') or (content_desc and content_desc == 'Clock') or \
               (text and 'Clock' in text) or (content_desc and 'Clock' in content_desc):
                return ('click', AppiumBy.ACCESSIBILITY_ID, 'Clock')
    elif "Timer" in goal:
        # Look for Timer tab or button
        for elem in elements:
            text = elem.get('text', '')
            content_desc = elem.get('content-desc', '')
            if (text and text == 'Timer') or (content_desc and content_desc == 'Timer') or \
               (text and 'Timer' in text) or (content_desc and 'Timer' in content_desc):
                return ('click', AppiumBy.ACCESSIBILITY_ID, 'Timer')
    elif "Stopwatch" in goal:
        # Look for Stopwatch tab or button
        for elem in elements:
            text = elem.get('text', '')
            content_desc = elem.get('content-desc', '')
            if (text and text == 'Stopwatch') or (content_desc and content_desc == 'Stopwatch') or \
               (text and 'Stopwatch' in text) or (content_desc and 'Stopwatch' in content_desc):
                return ('click', AppiumBy.ACCESSIBILITY_ID, 'Stopwatch')
    
    print("AI Decision: Goal not understood in this simple simulation.")
    return None

# --- /AI Simulation --- 