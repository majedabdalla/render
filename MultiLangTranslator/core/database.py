"""
Database operations module for MultiLangTranslator Bot

This module provides functions for handling user data, payments,
and other persistent storage needs.
"""

import json
import os
import logging
import time
import threading
from typing import Dict, Any, List, Optional

# Initialize logger
logger = logging.getLogger(__name__)

# Thread lock for file operations
file_locks = {}


def get_file_lock(file_path: str) -> threading.RLock:
    """Get a lock for a specific file to ensure thread safety."""
    if file_path not in file_locks:
        file_locks[file_path] = threading.RLock()
    return file_locks[file_path]


def ensure_directory_exists(file_path: str) -> None:
    """Ensure the directory for a file exists."""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")


def load_json_file(file_path: str, default: Any = None) -> Any:
    """
    Load data from a JSON file with thread safety.
    
    Args:
        file_path: Path to the JSON file
        default: Default value if file doesn't exist or has errors
        
    Returns:
        Loaded data or default value
    """
    with get_file_lock(file_path):
        try:
            ensure_directory_exists(file_path)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.info(
                    f"File not found: {file_path}, returning default value")
                return default if default is not None else {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {file_path}: {e}")
            return default if default is not None else {}
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            return default if default is not None else {}


def save_json_file(file_path: str, data: Any) -> bool:
    """
    Save data to a JSON file with thread safety.
    
    Args:
        file_path: Path to the JSON file
        data: Data to save
        
    Returns:
        True if successful, False otherwise
    """
    with get_file_lock(file_path):
        try:
            ensure_directory_exists(file_path)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving to {file_path}: {e}")
            return False


class DatabaseManager:
    """
    Advanced database manager for handling user data and other persistent storage.
    
    Features:
    - Thread-safe operations
    - Automatic backup
    - Data validation
    - Query capabilities
    """

    def __init__(self,
                 user_data_file: str,
                 pending_payments_file: str,
                 backup_interval: int = 3600,
                 max_backups: int = 5):
        """
        Initialize the database manager.
        
        Args:
            user_data_file: Path to user data file
            pending_payments_file: Path to pending payments file
            backup_interval: Interval between backups in seconds
            max_backups: Maximum number of backup files to keep
        """
        self.user_data_file = user_data_file
        self.pending_payments_file = pending_payments_file
        self.backup_interval = backup_interval
        self.max_backups = max_backups

        # Initialize data
        self._load_data()

        # Start backup thread
        self.backup_thread = threading.Thread(
            target=self._backup_data_periodically, daemon=True)
        self.backup_thread.start()

    def _load_data(self):
        """Load all data from files."""
        self.user_data = load_json_file(self.user_data_file, default={})
        self.pending_payments = load_json_file(self.pending_payments_file,
                                               default={})
        logger.info(
            f"Loaded data: {len(self.user_data)} users, {len(self.pending_payments)} pending payments"
        )

    def _save_data(self):
        """Save all data to files."""
        save_json_file(self.user_data_file, self.user_data)
        save_json_file(self.pending_payments_file, self.pending_payments)

    def _create_backup(self):
        """Create backup of all data files."""
        timestamp = int(time.time())

        # Backup user data
        user_data_backup = f"{self.user_data_file}.{timestamp}.bak"
        save_json_file(user_data_backup, self.user_data)

        # Backup pending payments
        payments_backup = f"{self.pending_payments_file}.{timestamp}.bak"
        save_json_file(payments_backup, self.pending_payments)

        logger.info(f"Created backup at {timestamp}")

        # Clean up old backups
        self._cleanup_old_backups()

    def _cleanup_old_backups(self):
        """Remove old backup files, keeping only the most recent ones."""
        try:
            # Get user data backups
            user_data_dir = os.path.dirname(self.user_data_file)
            user_data_base = os.path.basename(self.user_data_file)
            user_backups = [
                f for f in os.listdir(user_data_dir)
                if f.startswith(user_data_base) and f.endswith('.bak')
            ]

            # Get payment backups
            payment_dir = os.path.dirname(self.pending_payments_file)
            payment_base = os.path.basename(self.pending_payments_file)
            payment_backups = [
                f for f in os.listdir(payment_dir)
                if f.startswith(payment_base) and f.endswith('.bak')
            ]

            # Sort by timestamp (newest first)
            user_backups.sort(reverse=True)
            payment_backups.sort(reverse=True)

            # Remove excess backups
            for old_backup in user_backups[self.max_backups:]:
                os.remove(os.path.join(user_data_dir, old_backup))
                logger.debug(f"Removed old backup: {old_backup}")

            for old_backup in payment_backups[self.max_backups:]:
                os.remove(os.path.join(payment_dir, old_backup))
                logger.debug(f"Removed old backup: {old_backup}")

        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")

    def _backup_data_periodically(self):
        """Background thread to periodically backup data."""
        while True:
            try:
                time.sleep(self.backup_interval)
                self._create_backup()
            except Exception as e:
                logger.error(f"Error in backup thread: {e}")

    # User data methods
    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get data for a specific user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User data dictionary
        """
        user_id_str = str(user_id)
        with get_file_lock(self.user_data_file):
            return self.user_data.get(user_id_str, {})

    def update_user_data(self, user_id: str, data: Dict[str, Any]) -> None:
        """
        Update data for a specific user.
        
        Args:
            user_id: Telegram user ID
            data: Data to update
        """
        user_id_str = str(user_id)
        with get_file_lock(self.user_data_file):
            if user_id_str not in self.user_data:
                self.user_data[user_id_str] = {}

            self.user_data[user_id_str].update(data)
            save_json_file(self.user_data_file, self.user_data)

    def update_user_field(self, user_id: str, field: str, value: str) -> None:
        """
        Update a specific field in the user's data.

        Args:
            user_id: Telegram user ID
            field: Field name to update (e.g., "language", "gender")
            value: New value
        """
        user_id_str = str(user_id)
        with get_file_lock(self.user_data_file):
            if user_id_str not in self.user_data:
                self.user_data[user_id_str] = {}
            self.user_data[user_id_str][field] = value
            save_json_file(self.user_data_file, self.user_data)

    def delete_user_data(self, user_id: str) -> bool:
        """
        Delete data for a specific user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user was found and deleted, False otherwise
        """
        user_id_str = str(user_id)
        with get_file_lock(self.user_data_file):
            if user_id_str in self.user_data:
                del self.user_data[user_id_str]
                save_json_file(self.user_data_file, self.user_data)
                return True
            return False

    def get_all_users(self) -> List[str]:
        """
        Get a list of all user IDs.
        
        Returns:
            List of user IDs
        """
        with get_file_lock(self.user_data_file):
            return list(self.user_data.keys())

    def query_users(self, criteria: Dict[str, Any]) -> List[str]:
        """
        Query users based on criteria.
        
        Args:
            criteria: Dictionary of field-value pairs to match
            
        Returns:
            List of matching user IDs
        """
        matching_users = []

        with get_file_lock(self.user_data_file):
            for user_id, user_data in self.user_data.items():
                if all(
                        user_data.get(key) == value
                        for key, value in criteria.items()):
                    matching_users.append(user_id)

        return matching_users

    # Payment methods
    def add_pending_payment(self, user_id: str,
                            payment_data: Dict[str, Any]) -> str:
        """
        Add a pending payment.
        
        Args:
            user_id: Telegram user ID
            payment_data: Payment details
            
        Returns:
            Payment ID
        """
        user_id_str = str(user_id)
        payment_id = f"payment_{int(time.time())}_{user_id_str}"

        with get_file_lock(self.pending_payments_file):
            self.pending_payments[payment_id] = {
                "user_id": user_id_str,
                "timestamp": int(time.time()),
                "status": "pending",
                **payment_data
            }
            save_json_file(self.pending_payments_file, self.pending_payments)

        return payment_id

    def update_payment_status(self,
                              payment_id: str,
                              status: str,
                              admin_id: Optional[str] = None) -> bool:
        """
        Update payment status.
        
        Args:
            payment_id: Payment ID
            status: New status (approved, rejected)
            admin_id: ID of admin who processed the payment
            
        Returns:
            True if payment was found and updated, False otherwise
        """
        with get_file_lock(self.pending_payments_file):
            if payment_id in self.pending_payments:
                self.pending_payments[payment_id].update({
                    "status":
                    status,
                    "processed_at":
                    int(time.time()),
                    "processed_by":
                    admin_id
                })
                save_json_file(self.pending_payments_file,
                               self.pending_payments)

                # If approved, update user's premium status
                if status == "approved":
                    user_id = self.pending_payments[payment_id]["user_id"]
                    self.update_user_data(user_id, {"premium": True})

                return True
            return False

    def get_pending_payments(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all pending payments.
        
        Returns:
            Dictionary of payment ID to payment data
        """
        with get_file_lock(self.pending_payments_file):
            return {
                pid: data
                for pid, data in self.pending_payments.items()
                if data.get("status") == "pending"
            }

    def get_user_payments(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all payments for a specific user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of payment data dictionaries
        """
        user_id_str = str(user_id)
        with get_file_lock(self.pending_payments_file):
            return [{
                **data, "payment_id": pid
            } for pid, data in self.pending_payments.items()
                    if data.get("user_id") == user_id_str]


# Create a global database manager instance
db_manager = None


def init_database_manager(user_data_file: str, pending_payments_file: str):
    """
    Initialize the global database manager.
    
    Args:
        user_data_file: Path to user data file
        pending_payments_file: Path to pending payments file
    """
    global db_manager
    db_manager = DatabaseManager(user_data_file, pending_payments_file)
    return db_manager


def get_database_manager() -> DatabaseManager:
    """
    Get the global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global db_manager
    if db_manager is None:
        raise RuntimeError(
            "Database manager not initialized. Call init_database_manager first."
        )
    return db_manager


# Backward compatibility functions
def get_user_data(user_id: str) -> Dict[str, Any]:
    """Get data for a specific user (compatibility function)."""
    return get_database_manager().get_user_data(user_id)


def update_user_data(user_id: str, data: Dict[str, Any]) -> None:
    """Update data for a specific user (compatibility function)."""
    get_database_manager().update_user_data(user_id, data)
