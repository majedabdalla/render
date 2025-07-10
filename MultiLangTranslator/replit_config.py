"""
Replit-specific configuration and setup for MultiLangTranslator Bot

This module provides Replit-specific configurations and utilities to ensure
the bot runs smoothly on the Replit platform.
"""

import os
import logging
import threading
import time
from dotenv import load_dotenv

# Initialize logger
logger = logging.getLogger(__name__)

def load_environment_variables():
    """
    Load environment variables from .env file or Replit Secrets.
    
    Returns:
        Dictionary of loaded environment variables
    """
    # First try to load from .env file
    load_dotenv()
    
    # Check if we're running on Replit
    is_replit = "REPL_ID" in os.environ
    
    env_vars = {
        "BOT_TOKEN": os.getenv("BOT_TOKEN"),
        "ADMIN_ID": os.getenv("ADMIN_ID"),
        "TARGET_GROUP_ID": os.getenv("TARGET_GROUP_ID"),
        "PAYEER_ACCOUNT": os.getenv("PAYEER_ACCOUNT"),
        "BITCOIN_ADDRESS": os.getenv("BITCOIN_ADDRESS"),
        "PORT": os.getenv("PORT", "8080"),
        "SESSION_SECRET": os.getenv("SESSION_SECRET", "multichatbot_secret_key"),
        "IS_REPLIT": is_replit
    }
    
    # Log loaded variables (excluding sensitive ones)
    logger.info(f"Environment loaded. Running on Replit: {is_replit}")
    
    return env_vars

def setup_replit_specific_config():
    """
    Set up Replit-specific configurations.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create .replit file if it doesn't exist
        if not os.path.exists(".replit"):
            with open(".replit", "w") as f:
                f.write("language = \"python3\"\n")
                f.write("run = \"python main.py\"\n")
            logger.info("Created .replit file")
        
        # Create replit.nix file if it doesn't exist
        if not os.path.exists("replit.nix"):
            with open("replit.nix", "w") as f:
                f.write("{ pkgs }: {\n")
                f.write("  deps = [\n")
                f.write("    pkgs.python310\n")
                f.write("    pkgs.python310Packages.pip\n")
                f.write("    pkgs.python310Packages.flask\n")
                f.write("    pkgs.python310Packages.python-telegram-bot\n")
                f.write("    pkgs.python310Packages.psutil\n")
                f.write("    pkgs.python310Packages.python-dotenv\n")
                f.write("  ];\n")
                f.write("}\n")
            logger.info("Created replit.nix file")
        
        return True
    except Exception as e:
        logger.error(f"Error setting up Replit-specific config: {e}")
        return False

def keep_replit_alive():
    """
    Start a background thread to keep Replit alive by periodically writing to a file.
    This helps prevent the Replit from going to sleep due to inactivity.
    """
    def ping_worker():
        ping_file = ".replit_ping"
        while True:
            try:
                # Write current timestamp to ping file
                with open(ping_file, "w") as f:
                    f.write(f"PING: {time.time()}")
                
                # Sleep for 5 minutes
                time.sleep(300)
            except Exception as e:
                logger.error(f"Error in ping worker: {e}")
                time.sleep(60)  # Sleep for 1 minute on error
    
    # Start ping worker in a daemon thread
    ping_thread = threading.Thread(target=ping_worker, daemon=True)
    ping_thread.start()
    logger.info("Started Replit keep-alive ping thread")

def check_replit_health():
    """
    Check the health of the Replit environment.
    
    Returns:
        Dictionary with health check results
    """
    import psutil
    
    results = {
        "status": "ok",
        "issues": []
    }
    
    # Check CPU usage
    cpu_percent = psutil.cpu_percent()
    if cpu_percent > 90:
        results["status"] = "warning"
        results["issues"].append(f"High CPU usage: {cpu_percent}%")
    
    # Check memory usage
    memory = psutil.virtual_memory()
    if memory.percent > 90:
        results["status"] = "warning"
        results["issues"].append(f"High memory usage: {memory.percent}%")
    
    # Check disk usage
    disk = psutil.disk_usage('/')
    if disk.percent > 90:
        results["status"] = "warning"
        results["issues"].append(f"High disk usage: {disk.percent}%")
    
    # Check if we're running on Replit
    if "REPL_ID" not in os.environ:
        results["status"] = "warning"
        results["issues"].append("Not running on Replit")
    
    return results

# Initialize when module is imported
if __name__ != "__main__":
    # Load environment variables
    env_vars = load_environment_variables()
    
    # Set up Replit-specific config if running on Replit
    if env_vars["IS_REPLIT"]:
        setup_replit_specific_config()
        keep_replit_alive()
