import os
# Contains absolute paths of all the important folders in code

PROJECT_DIR = (str(os.path.realpath(__file__)))[:-35]

# Data folder
DATA_DIR = os.path.join(PROJECT_DIR, "data")

RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")

RAW_STATIC_DATA_DIR = os.path.join(DATA_DIR, "raw", "static")

INTERMEDIATE_DATA_DIR = os.path.join(DATA_DIR, "intermediate")

PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")

# src folder
SRC_DIR = os.path.join(PROJECT_DIR, "src")

# model object directory
Model_DIR = os.path.join(PROJECT_DIR, "model_object")

# output folder
OUTPUT_DIR = os.path.join(PROJECT_DIR, "outputs")


# Log folder
LOG_DIR = os.path.join(PROJECT_DIR, "logs")

# Config folder
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")

# Path to the script
clear_notebook_output_script_path = os.path.join(CONFIG_DIR, "clear_notebook_output.py")