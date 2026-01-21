
import json
import traceback

def test_key_error():
    print("Testing KeyError string representation...")
    try:
        # Simulate the error seen in the screenshot
        raise KeyError('\n "title"')
    except Exception as e:
        print(f"Exception type: {type(e)}")
        print(f"Exception str: {str(e)}")
        print(f"Exception repr: {repr(e)}")

def test_json_repair_behavior():
    print("\nTesting json_repair behavior (if installed)...")
    try:
        from json_repair import repair_json
        # Test with broken JSON that might cause issues
        bad_json = '{\n "title": "Test"'
        print(f"Repairing: {repr(bad_json)}")
        repaired = repair_json(bad_json)
        print(f"Repaired: {repr(repaired)}")
        parsed = json.loads(repaired)
        print(f"Parsed: {parsed}")
    except ImportError:
        print("json_repair not installed")
    except Exception as e:
        print(f"Error in json_repair test: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_key_error()
    test_json_repair_behavior()
