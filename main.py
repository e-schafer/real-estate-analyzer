import os
import subprocess
import sys


def main():
    """
    Main entry point for the Real Estate Market Analyzer application.
    Launches the Streamlit app.
    """
    print("Starting Real Estate Market Analyzer...")

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Launch the Streamlit app
    cmd = [sys.executable, "-m", "streamlit", "run", os.path.join(script_dir, "app.py")]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
    except Exception as e:
        print(f"Error running Streamlit app: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
