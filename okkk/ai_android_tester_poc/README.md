# AI Android Test Agent PoC

A proof-of-concept implementation of an AI-powered test agent for Android apps, focusing on the Android Clock app as an example.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Appium

1. Install Appium Server (if not already installed):
   ```bash
   npm install -g appium
   ```

2. Install the UiAutomator2 driver for Android:
   ```bash
   appium driver install uiautomator2
   ```

3. Start the Appium server:
   ```bash
   appium
   ```

### 3. Configure Your Android Device/Emulator

1. Ensure an Android device is connected via USB or an emulator is running
2. Enable USB debugging (for physical devices)
3. Install the Clock app if not already present

### 4. Adjust Configuration

Edit `utils/appium_handler.py` to match your environment:

```python
# Example configuration
CAPABILITIES = {
    'platformName': 'Android',
    'automationName': 'UiAutomator2',
    'deviceName': 'Android Emulator',  # Change to your device name or use UDID
    # 'udid': 'YOUR_DEVICE_UDID',      # Uncomment and add your device UDID for physical devices
    'appPackage': 'com.google.android.deskclock',
    'appActivity': 'com.android.deskclock.DeskClock',
    'noReset': True,
    'fullReset': False,
    'language': 'en',
    'locale': 'US'
}
```

#### Finding Device Information

To find your device information:

```bash
# List all connected devices
adb devices

# Find app package and activity (while app is open)
adb shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'
```

### 5. Run Tests

```bash
pytest -s -v
```

The `-s` flag shows print statements for better debugging visibility.

## Project Structure

- `tests/` - Contains test cases
  - `test_clock_navigation.py` - Basic test that navigates through Clock app tabs
- `utils/` - Helper modules
  - `appium_handler.py` - Manages Appium connection and interactions
  - `ui_analyzer.py` - Simulates AI agent for UI parsing and decision making

## Extending the Project

To integrate with an actual LLM like Gemini:

1. Add the Gemini/OpenAI SDK to `requirements.txt`
2. Modify `ui_analyzer.py` to format UI data for the LLM
3. Implement proper prompt construction and response parsing
4. Replace the simulated decision logic with real LLM calls 