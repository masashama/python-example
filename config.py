import re

GOOGLE_SHEET = "https://script.google.com/macros/s/AKfycbxeexe3L_t5OVb_bvAEgb6Bwf98vbLH_7xbdv9qaoFlal7XK4ob/exec"
TOKEN = "296172584:AAGvSF-uAjR9qPZjqUFskD1AHZQmYsK_6X0"
TOKEN = "278233013:AAF77OxhW9gePbGG1IYvB504JED-xm-btVQ"

AMOUNT_REGEXP = re.compile(r'^(\d+\.?\d*)', re.IGNORECASE)
PAYSYTEM_REGEXP = re.compile(r'^\d+\.?\d* (\w+)', re.IGNORECASE)
COSTS_REGEXP = re.compile(r'^\d+\.?\d* \w+ ([\w /]+)$', re.IGNORECASE)
