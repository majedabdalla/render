"""
Data directory initialization and validation module for MultiLangTranslator Bot

This module ensures all required directories and files exist and are properly
initialized before the bot starts.
"""

import os
import json
import logging
import shutil
from typing import Dict, Any, List

# Initialize logger
logger = logging.getLogger(__name__)

def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            logger.info(f"Created directory: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False

def ensure_file_exists(file_path: str, default_content: Any = None) -> bool:
    """
    Ensure a file exists, creating it with default content if necessary.
    
    Args:
        file_path: Path to the file
        default_content: Default content to write if file doesn't exist
        
    Returns:
        True if successful, False otherwise
    """
    try:
        directory = os.path.dirname(file_path)
        ensure_directory_exists(directory)
        
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                if default_content is not None:
                    if isinstance(default_content, (dict, list)):
                        json.dump(default_content, f, ensure_ascii=False, indent=2)
                    else:
                        f.write(str(default_content))
                else:
                    # Default to empty JSON object if no content provided
                    json.dump({}, f)
            logger.info(f"Created file with default content: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error ensuring file exists {file_path}: {e}")
        return False

def copy_file_if_not_exists(source_path: str, target_path: str) -> bool:
    """
    Copy a file if the target doesn't exist.
    
    Args:
        source_path: Path to the source file
        target_path: Path to the target file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if os.path.exists(source_path) and not os.path.exists(target_path):
            directory = os.path.dirname(target_path)
            ensure_directory_exists(directory)
            
            shutil.copy2(source_path, target_path)
            logger.info(f"Copied file from {source_path} to {target_path}")
            return True
        return os.path.exists(target_path)
    except Exception as e:
        logger.error(f"Error copying file from {source_path} to {target_path}: {e}")
        return False

def validate_json_file(file_path: str) -> bool:
    """
    Validate that a file contains valid JSON.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        True if valid JSON, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Error validating JSON file {file_path}: {e}")
        return False

def repair_json_file(file_path: str, default_content: Any = None) -> bool:
    """
    Attempt to repair a corrupted JSON file.
    
    Args:
        file_path: Path to the JSON file
        default_content: Default content to use if repair fails
        
    Returns:
        True if repaired successfully, False otherwise
    """
    try:
        # If file doesn't exist or validation passes, no repair needed
        if not os.path.exists(file_path) or validate_json_file(file_path):
            return ensure_file_exists(file_path, default_content)
        
        # Try to read the file and parse it line by line
        valid_content = None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    valid_content = json.loads(content)
        except:
            pass
        
        # If parsing failed, create backup and use default content
        if valid_content is None:
            backup_path = f"{file_path}.bak"
            if os.path.exists(file_path):
                shutil.copy2(file_path, backup_path)
                logger.info(f"Created backup of corrupted file: {backup_path}")
            
            return ensure_file_exists(file_path, default_content)
        
        return True
    except Exception as e:
        logger.error(f"Error repairing JSON file {file_path}: {e}")
        return False

def initialize_data_directories(config) -> bool:
    """
    Initialize all required data directories and files.
    
    Args:
        config: Configuration module
        
    Returns:
        True if successful, False otherwise
    """
    success = True
    
    # Ensure data directory exists
    data_dir = os.path.dirname(config.USER_DATA_FILE)
    success &= ensure_directory_exists(data_dir)
    
    # Ensure locales directory exists
    success &= ensure_directory_exists(config.LOCALES_DIR)
    
    # Ensure user data file exists
    success &= ensure_file_exists(config.USER_DATA_FILE, {})
    
    # Ensure pending payments file exists
    success &= ensure_file_exists(config.PENDING_PAYMENTS_FILE, {})
    
    # Ensure regions countries file exists
    regions_countries = {
        "Asia": [
            "Afghanistan", "Bahrain", "Bangladesh", "Bhutan", "Brunei", "Cambodia", "China", "India", 
            "Indonesia", "Iran", "Iraq", "Israel", "Japan", "Jordan", "Kazakhstan", "Kuwait", "Kyrgyzstan", 
            "Laos", "Lebanon", "Malaysia", "Maldives", "Mongolia", "Myanmar", "Nepal", "North Korea", 
            "Oman", "Pakistan", "Palestine State", "Philippines", "Qatar", "Saudi Arabia", "Singapore", 
            "South Korea", "Sri Lanka", "Syria", "Taiwan", "Tajikistan", "Thailand", "Timor-Leste", 
            "Turkey", "Turkmenistan", "United Arab Emirates", "Uzbekistan", "Vietnam", "Yemen"
        ],
        "Europe": [
            "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium", 
            "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Denmark", 
            "Estonia", "Finland", "France", "Georgia", "Germany", "Greece", "Hungary", "Iceland", 
            "Ireland", "Italy", "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta", 
            "Moldova", "Monaco", "Montenegro", "Netherlands", "North Macedonia", "Norway", "Poland", 
            "Portugal", "Romania", "Russia", "San Marino", "Serbia", "Slovakia", "Slovenia", "Spain", 
            "Sweden", "Switzerland", "Ukraine", "United Kingdom", "Vatican City"
        ],
        "Africa": [
            "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", "Cabo Verde", 
            "Cameroon", "Central African Republic", "Chad", "Comoros", "Congo, Democratic Republic of the", 
            "Congo, Republic of the", "Cote d'Ivoire", "Djibouti", "Egypt", "Equatorial Guinea", 
            "Eritrea", "Eswatini", "Ethiopia", "Gabon", "Gambia", "Ghana", "Guinea", "Guinea-Bissau", 
            "Kenya", "Lesotho", "Liberia", "Libya", "Madagascar", "Malawi", "Mali", "Mauritania", 
            "Mauritius", "Morocco", "Mozambique", "Namibia", "Niger", "Nigeria", "Rwanda", 
            "Sao Tome and Principe", "Senegal", "Seychelles", "Sierra Leone", "Somalia", "South Africa", 
            "South Sudan", "Sudan", "Tanzania", "Togo", "Tunisia", "Uganda", "Zambia", "Zimbabwe"
        ],
        "North America": [
            "Antigua and Barbuda", "Bahamas", "Barbados", "Belize", "Canada", "Costa Rica", "Cuba", 
            "Dominica", "Dominican Republic", "El Salvador", "Grenada", "Guatemala", "Haiti", "Honduras", 
            "Jamaica", "Mexico", "Nicaragua", "Panama", "Saint Kitts and Nevis", "Saint Lucia", 
            "Saint Vincent and the Grenadines", "United States of America"
        ],
        "South America": [
            "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador", "Guyana", "Paraguay", 
            "Peru", "Suriname", "Uruguay", "Venezuela"
        ],
        "Oceania": [
            "Australia", "Fiji", "Kiribati", "Marshall Islands", "Micronesia", "Nauru", "New Zealand", 
            "Palau", "Papua New Guinea", "Samoa", "Solomon Islands", "Tonga", "Tuvalu", "Vanuatu"
        ]
    }
    success &= ensure_file_exists(config.REGIONS_COUNTRIES_FILE, regions_countries)
    
    # Copy language files from attached_assets if they don't exist
    for lang_code in config.SUPPORTED_LANGUAGES.keys():
        source_file = os.path.join("attached_assets", f"{lang_code}.json")
        target_file = os.path.join(config.LOCALES_DIR, f"{lang_code}.json")
        success &= copy_file_if_not_exists(source_file, target_file)
    
    # Ensure sessions directory exists
    sessions_file = "data/sessions.json"
    success &= ensure_file_exists(sessions_file, {})
    
    return success

def validate_and_repair_data_files(config) -> Dict[str, bool]:
    """
    Validate and repair all data files if needed.
    
    Args:
        config: Configuration module
        
    Returns:
        Dictionary with validation results for each file
    """
    results = {}
    
    # Validate and repair user data file
    results["user_data"] = repair_json_file(config.USER_DATA_FILE, {})
    
    # Validate and repair pending payments file
    results["pending_payments"] = repair_json_file(config.PENDING_PAYMENTS_FILE, {})
    
    # Validate and repair regions countries file
    regions_countries = {
        "Asia": ["China", "India", "Japan"],
        "Europe": ["Germany", "France", "United Kingdom"],
        "Africa": ["Egypt", "Nigeria", "South Africa"],
        "North America": ["United States", "Canada", "Mexico"],
        "South America": ["Brazil", "Argentina", "Colombia"],
        "Oceania": ["Australia", "New Zealand"]
    }
    results["regions_countries"] = repair_json_file(config.REGIONS_COUNTRIES_FILE, regions_countries)
    
    # Validate and repair sessions file
    sessions_file = "data/sessions.json"
    results["sessions"] = repair_json_file(sessions_file, {})
    
    # Validate language files
    for lang_code in config.SUPPORTED_LANGUAGES.keys():
        lang_file = os.path.join(config.LOCALES_DIR, f"{lang_code}.json")
        results[f"lang_{lang_code}"] = validate_json_file(lang_file)
    
    return results
