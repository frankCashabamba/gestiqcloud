import sys
import os

# Add the app directory to the Python path before tests run
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
