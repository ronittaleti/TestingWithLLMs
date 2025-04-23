import json
import os
import time
from typing import List, Dict, Any
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
from ai_android_tester_poc.utils.appium_handler import AppiumHandler, AppiumBy

# Load environment variables
load_dotenv()

# Configure Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it in your .env file.")

genai.configure(api_key=GOOGLE_API_KEY)
MODEL_NAME = os.getenv('MODEL_NAME', 'gemini-1.5-pro')

class TestCaseGenerator:
    def __init__(self, appium_handler: AppiumHandler):
        self.appium_handler = appium_handler
        try:
            self.model = genai.GenerativeModel(MODEL_NAME)
            self.llm = GoogleGenerativeAI(
                model=MODEL_NAME,
                google_api_key=GOOGLE_API_KEY,
                temperature=0.7,
                convert_system_message_to_human=True
            )
            print(f"Successfully initialized Gemini model: {MODEL_NAME}")
        except Exception as e:
            print(f"Error initializing Gemini model: {e}")
            raise
        
        # Define prompt templates
        self.test_case_prompt = PromptTemplate(
            input_variables=["app_info", "ui_elements", "current_screen"],
            template="""
            You are an expert QA engineer specializing in automated test case generation for Android apps.
            
            Current App Information:
            {app_info}
            
            Current Screen Elements:
            {ui_elements}
            
            Current Screen Context:
            {current_screen}
            
            Your task is to generate comprehensive test cases based on the UI elements and app context.
            For each test case, include:
            1. Test case ID and title
            2. Preconditions
            3. Test steps
            4. Expected results
            5. Assertions
            6. Priority level
            7. Test type (functional, UI, etc.)
            
            Format the output as a JSON array of test cases with the following structure:
            [
                {{
                    "test_case_id": "TC-001",
                    "title": "Test case title",
                    "description": "Detailed description",
                    "preconditions": ["Precondition 1", "Precondition 2"],
                    "steps": [
                        {{
                            "step_number": 1,
                            "action": "Action description",
                            "element": {{
                                "type": "element type",
                                "identifier": "element identifier",
                                "value": "element value"
                            }},
                            "expected_result": "Expected result"
                        }}
                    ],
                    "assertions": ["Assertion 1", "Assertion 2"],
                    "priority": "High/Medium/Low",
                    "test_type": "Functional/UI/Performance",
                    "tags": ["tag1", "tag2"]
                }}
            ]
            
            Focus on generating:
            1. Functional test cases for core features
            2. UI test cases for layout and interaction
            3. Edge cases and error scenarios
            4. Navigation flows
            5. Data validation cases
            
            Ensure test cases are:
            - Independent and self-contained
            - Have clear success criteria
            - Include proper assertions
            - Cover both positive and negative scenarios
            """
        )
        
        self.test_chain = LLMChain(llm=self.llm, prompt=self.test_case_prompt)

    def analyze_screen(self) -> Dict[str, Any]:
        """Analyzes the current screen and returns UI information."""
        print("\nAnalyzing current screen...")
        page_source = self.appium_handler.get_page_source()
        if not page_source:
            print("Warning: Could not get page source")
            return {}
            
        elements = self.appium_handler.get_actionable_elements(page_source)
        print(f"Found {len(elements)} actionable elements")
        
        current_activity = self.appium_handler.driver.current_activity if self.appium_handler.driver else None
        print(f"Current activity: {current_activity}")
        
        return {
            "current_activity": current_activity,
            "elements": elements,
            "screen_info": {
                "package": self.appium_handler.driver.current_package if self.appium_handler.driver else None,
                "activity": current_activity,
                "orientation": self.appium_handler.driver.orientation if self.appium_handler.driver else None
            }
        }

    def generate_test_cases(self) -> List[Dict[str, Any]]:
        """Generates test cases based on the current app state."""
        print("\nGenerating test cases...")
        screen_info = self.analyze_screen()
        
        if not screen_info.get("elements"):
            print("No UI elements found to generate test cases from")
            return []
        
        # Format UI elements for the prompt
        formatted_elements = self._format_elements_for_prompt(screen_info["elements"])
        print(f"\nFormatted UI elements:\n{formatted_elements}")
        
        try:
            # Generate test cases using the LLM
            print("\nSending request to Gemini...")
            response = self.test_chain.run(
                app_info=json.dumps(screen_info["screen_info"], indent=2),
                ui_elements=formatted_elements,
                current_screen=screen_info["current_activity"]
            )
            print("\nReceived response from Gemini")
            
            try:
                # Clean the response by removing markdown code block markers and comments
                cleaned_response = response.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]  # Remove ```json
                if cleaned_response.startswith('```'):
                    cleaned_response = cleaned_response[3:]  # Remove ```
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]  # Remove ```
                cleaned_response = cleaned_response.strip()
                
                # Remove any comments from the JSON
                cleaned_response = '\n'.join(
                    line for line in cleaned_response.split('\n')
                    if not line.strip().startswith('//')
                )
                
                print("Cleaned response:", cleaned_response)
                test_cases = json.loads(cleaned_response)
                print(f"Successfully parsed {len(test_cases)} test cases")
                return test_cases
            except json.JSONDecodeError as e:
                print(f"Error parsing test cases from LLM response: {e}")
                print(f"Raw response: {response}")
                return []
        except Exception as e:
            print(f"Error generating test cases: {e}")
            return []

    def _format_elements_for_prompt(self, elements: List[Dict[str, Any]]) -> str:
        """Formats UI elements into a readable string for the prompt."""
        formatted = []
        for elem in elements:
            element_info = []
            if elem.get('text'):
                element_info.append(f"Text: {elem['text']}")
            if elem.get('content-desc'):
                element_info.append(f"Description: {elem['content-desc']}")
            if elem.get('resource-id'):
                element_info.append(f"Resource ID: {elem['resource-id']}")
            if elem.get('class'):
                element_info.append(f"Type: {elem['class']}")
            if elem.get('clickable') == 'true':
                element_info.append("Clickable")
            
            if element_info:
                formatted.append(" - " + ", ".join(element_info))
        
        return "\n".join(formatted)

    def save_test_cases(self, test_cases: List[Dict[str, Any]], filename: str = "generated_test_cases.json"):
        """Saves generated test cases to a JSON file."""
        if not test_cases:
            print("Warning: No test cases to save")
            return
            
        try:
            with open(filename, 'w') as f:
                json.dump(test_cases, f, indent=2)
            print(f"Successfully saved {len(test_cases)} test cases to {filename}")
        except Exception as e:
            print(f"Error saving test cases: {e}")

    def crawl_app(self, max_screens: int = 10):
        """Crawls through the app to discover different screens and generate test cases."""
        print(f"\nStarting app crawl (max screens: {max_screens})")
        visited_screens = set()
        all_test_cases = []
        
        while len(visited_screens) < max_screens:
            current_activity = self.appium_handler.driver.current_activity
            if current_activity in visited_screens:
                print(f"Already visited {current_activity}, stopping crawl")
                break
                
            visited_screens.add(current_activity)
            print(f"\nAnalyzing screen: {current_activity}")
            
            # Generate test cases for current screen
            screen_test_cases = self.generate_test_cases()
            if screen_test_cases:
                print(f"Generated {len(screen_test_cases)} test cases for {current_activity}")
                all_test_cases.extend(screen_test_cases)
            else:
                print(f"No test cases generated for {current_activity}")
            
            # Try to navigate to a new screen
            elements = self.appium_handler.get_actionable_elements(self.appium_handler.get_page_source())
            print(f"Found {len(elements)} elements to potentially click")
            
            clicked = False
            for elem in elements:
                if elem.get('clickable') == 'true':
                    try:
                        content_desc = elem.get('content-desc', '')
                        print(f"Attempting to click element with description: {content_desc}")
                        self.appium_handler.find_and_click(AppiumBy.ACCESSIBILITY_ID, content_desc)
                        print("Click successful")
                        time.sleep(2)  # Wait for screen transition
                        clicked = True
                        break
                    except Exception as e:
                        print(f"Error clicking element: {e}")
                        continue
            
            if not clicked:
                print("No clickable elements found, stopping crawl")
                break
        
        print(f"\nCrawl completed. Visited {len(visited_screens)} screens and generated {len(all_test_cases)} test cases")
        return all_test_cases 