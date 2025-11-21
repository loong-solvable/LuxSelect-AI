import sys
import os
import time

# Ensure the project root is in sys.path so imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from luxselect.src.core.ai_client import OpenAIClient

def run_live_test():
    """
    Runs a live test against the configured AI provider using real API calls.
    """
    print("="*60)
    print("LuxSelect Live AI Response Test")
    print("WARNING: This will consume your API quota!")
    print("="*60)

    # Check for API Key
    from luxselect.src.config import settings
    if not settings.OPENAI_API_KEY:
        print("Error: No API Key found in .env file.")
        print("Please configure OPENAI_API_KEY before running this test.")
        return

    client = OpenAIClient()

    test_cases = [
        ("文言文", "左司马"),
        ("技术", "PyQt6 signals"),
        ("流行语", "绝绝子"),
        ("命令", "chmod +x"),
    ]

    for category, text in test_cases:
        print(f"\n[Testing Scenario: {category}]")
        print(f"Input: {text}")
        print("-" * 30)
        print("AI Response: ", end="", flush=True)

        start_time = time.time()
        try:
            # Collect the stream and print in real-time
            for chunk in client.stream_explanation(text):
                print(chunk, end="", flush=True)
            
            duration = time.time() - start_time
            print(f"\n\n(Time taken: {duration:.2f}s)")
            
        except Exception as e:
            print(f"\n\n[FAILED] Error: {e}")

    print("\n" + "="*60)
    print("Test Complete.")

if __name__ == "__main__":
    run_live_test()

