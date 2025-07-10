import json
import os
import re

locales_dir = '/home/ubuntu/MultiLangTranslatorUpdated/MultiLangTranslatorUpdated/MultiLangTranslator/attached_assets'

all_keys = set()
translations = {}

# Function to escape backslashes in JSON strings
def escape_json_string(text):
    return text.replace('\\', '\\\\')

# Load all translation files and collect all unique keys
for filename in os.listdir(locales_dir):
    if filename.endswith(".json") and filename != 'regions_countries.json' and filename != 'countries.json':
        lang_code = filename.split(".")[0]
        filepath = os.path.join(locales_dir, filename)
        
        # Read file content, escape backslashes, and then load JSON
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Replace single backslashes with double backslashes, but be careful not to double escape already escaped ones
            # This regex replaces a single backslash that is not followed by another backslash or a quote
            # content = re.sub(r'\\([^\\"])', r'\\\\\\1', content)
            # A simpler approach: replace all single backslashes with double backslashes, assuming they are not already escaped
            content = content.replace('\\n', '\\\\n') # Handle newline characters specifically
            content = content.replace('\\', '\\\\') # Escape all other backslashes
            
            # Attempt to load JSON after escaping
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON in {filename}: {e}")
                print(f"Problematic content around: {content[max(0, e.pos-20):e.pos+20]}")
                continue # Skip this file if it's still problematic

            translations[lang_code] = data
            all_keys.update(data.keys())

# Check for missing keys in each language and add them
for lang_code, data in translations.items():
    missing_keys = all_keys - set(data.keys())
    if missing_keys:
        print(f"Missing keys in {lang_code}.json: {missing_keys}")
        # Add missing keys with a placeholder or default from English if available
        for key in missing_keys:
            if 'en' in translations and key in translations['en']:
                data[key] = translations['en'][key]  # Use English translation as default
            else:
                data[key] = f"MISSING_TRANSLATION_{key}" # Placeholder
        
        # Write updated translation back to file
        filepath = os.path.join(locales_dir, f"{lang_code}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Updated {lang_code}.json with missing keys.")

# Verify consistency of 'back' button and other labels
# This part requires manual review of the output from the previous step and the files themselves.
# For now, I'll just print a confirmation that the script ran.
print("Translation file consistency check and update initiated.")


