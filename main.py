"""Entry point for the refactored Launchpad MK2 Controller.

This script serves as the main entry point for the application.
Run this to start the Launchpad MK2 Spotify Controller.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import main

if __name__ == '__main__':
    sys.exit(main())
