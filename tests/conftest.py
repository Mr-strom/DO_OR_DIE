import sys
import os

# Guarantee root directory is in sys.path for all tests and AppTest runners
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
