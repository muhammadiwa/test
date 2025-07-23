"""
Configuration manager for dynamic configuration updates.
"""
import os
from loguru import logger
import json
from utils.config import Config

class ConfigManager:
    """Manager for dynamic configuration updates."""
    
    # Define which parameters can be configured via bot commands
    CONFIGURABLE_PARAMS = {
        'DEFAULT_USDT_AMOUNT': {
            'type': float,
            'min': 1.0,
            'max': 10000.0,
            'description': 'Default amount in USDT for trades'
        },
        'BUY_FREQUENCY_MS': {
            'type': int,
            'min': 1,
            'max': 1000,
            'description': 'Buy frequency in milliseconds (1-1000)'
        },
        'MAX_RETRY_ATTEMPTS': {
            'type': int,
            'min': 1,
            'max': 1000,
            'description': 'Maximum retry attempts for failed orders'
        },
        'RETRY_DELAY': {
            'type': float,
            'min': 0.01,
            'max': 10.0,
            'description': 'Delay between retry attempts in seconds'
        },
        'MIN_ORDER_USDT': {
            'type': float,
            'min': 1.0,
            'max': 10000.0,
            'description': 'Minimum order size in USDT'
        },
        'PROFIT_TARGET_PERCENTAGE': {
            'type': float,
            'min': 0.1,
            'max': 10000.0,
            'description': 'Take profit percentage'
        },
        'TP_SELL_PERCENTAGE': {
            'type': float,
            'min': 1.0,
            'max': 100.0,
            'description': 'Percentage of position to sell at take profit (1-100)'
        },
        'STOP_LOSS_PERCENTAGE': {
            'type': float,
            'min': 0.1,
            'max': 100.0,
            'description': 'Stop loss percentage'
        },
        'TRAILING_STOP_PERCENTAGE': {
            'type': float,
            'min': 0.0,
            'max': 100.0,
            'description': 'Trailing stop percentage (0 to disable)'
        },
        'TSL_MIN_ACTIVATION_PERCENTAGE': {
            'type': float,
            'min': 0.0,
            'max': 1000.0,
            'description': 'Minimum price increase percentage to activate TSL (0 to always activate)'
        },
        'TIME_BASED_SELL_MINUTES': {
            'type': int,
            'min': 1,
            'max': 1440,  # 24 hours
            'description': 'Time to auto-sell in minutes'
        },
    }
    
    def __init__(self, config_class=Config):
        """Initialize with a reference to the config class."""
        self.config_class = config_class
        self.env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        self.custom_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'custom_config.json')
        self.custom_config = self._load_custom_config()
    
    def _load_custom_config(self):
        """Load custom configuration from file if it exists."""
        if os.path.exists(self.custom_config_path):
            try:
                with open(self.custom_config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load custom config: {e}")
                # Try to create a new file if loading fails
                self._save_custom_config()
        else:
            # Create custom config file with empty dict if it doesn't exist
            try:
                with open(self.custom_config_path, 'w') as f:
                    json.dump({}, f, indent=4)
                logger.info(f"Created new custom config file at {self.custom_config_path}")
            except Exception as e:
                logger.error(f"Failed to create custom config file: {e}")
        return {}
    
    def _save_custom_config(self):
        """Save custom configuration to file."""
        try:
            with open(self.custom_config_path, 'w') as f:
                json.dump(self.custom_config, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Failed to save custom config: {e}")
            return False
    
    def get_parameter(self, param_name):
        """
        Get the current value of a parameter.
        
        Args:
            param_name: Name of the parameter to get
            
        Returns:
            Current value of the parameter or None if not found
        """
        # Check if parameter is configurable
        if param_name not in self.CONFIGURABLE_PARAMS:
            return None
        
        # Check if we have a custom value
        if param_name in self.custom_config:
            return self.custom_config[param_name]
        
        # Fall back to the value from Config
        if hasattr(self.config_class, param_name):
            return getattr(self.config_class, param_name)
        
        return None
    
    def set_parameter(self, param_name, value):
        """
        Set a new value for a parameter.
        
        Args:
            param_name: Name of the parameter to set
            value: New value for the parameter
            
        Returns:
            Tuple of (success, message)
        """
        # Check if parameter is configurable
        if param_name not in self.CONFIGURABLE_PARAMS:
            return False, f"Parameter '{param_name}' is not configurable."
        
        # Get parameter specifications
        param_spec = self.CONFIGURABLE_PARAMS[param_name]
        param_type = param_spec['type']
        
        # Convert value to correct type
        try:
            value = param_type(value)
        except ValueError:
            return False, f"Value must be a {param_type.__name__}."
        
        # Validate value against constraints
        if 'min' in param_spec and value < param_spec['min']:
            return False, f"Value must be at least {param_spec['min']}."
        
        if 'max' in param_spec and value > param_spec['max']:
            return False, f"Value must be at most {param_spec['max']}."
        
        # Store the value in custom config
        self.custom_config[param_name] = value
        
        # Save custom config
        if self._save_custom_config():
            # Also update the Config class attribute
            setattr(self.config_class, param_name, value)
            return True, f"Parameter '{param_name}' updated to {value}."
        else:
            return False, "Failed to save configuration."
    
    def reset_parameter(self, param_name):
        """
        Reset a parameter to its default value from .env file.
        
        Args:
            param_name: Name of the parameter to reset
            
        Returns:
            Tuple of (success, message)
        """
        # Check if parameter is configurable
        if param_name not in self.CONFIGURABLE_PARAMS:
            return False, f"Parameter '{param_name}' is not configurable."
        
        # Remove from custom config if present
        if param_name in self.custom_config:
            del self.custom_config[param_name]
            self._save_custom_config()
        
        # Reset the Config class attribute from environment
        default_value = os.getenv(param_name)
        if default_value is not None:
            param_type = self.CONFIGURABLE_PARAMS[param_name]['type']
            try:
                setattr(self.config_class, param_name, param_type(default_value))
                return True, f"Parameter '{param_name}' reset to default value: {default_value}."
            except ValueError:
                return False, f"Failed to reset parameter '{param_name}'. Invalid default value."
        else:
            return False, f"No default value found for parameter '{param_name}'."
    
    def reset_all_parameters(self):
        """
        Reset all parameters to their default values from .env file.
        
        Returns:
            Tuple of (success, message)
        """
        # Clear custom config
        self.custom_config = {}
        self._save_custom_config()
        
        # Reset all configurable parameters
        reset_count = 0
        for param_name in self.CONFIGURABLE_PARAMS:
            default_value = os.getenv(param_name)
            if default_value is not None:
                param_type = self.CONFIGURABLE_PARAMS[param_name]['type']
                try:
                    setattr(self.config_class, param_name, param_type(default_value))
                    reset_count += 1
                except ValueError:
                    logger.error(f"Failed to reset parameter '{param_name}'. Invalid default value.")
        
        return True, f"Reset {reset_count} parameters to their default values."
    
    def get_all_parameters(self):
        """
        Get all configurable parameters and their current values.
        
        Returns:
            Dictionary of parameter names and their values
        """
        result = {}
        for param_name in self.CONFIGURABLE_PARAMS:
            result[param_name] = self.get_parameter(param_name)
        return result
    
    def get_configurable_params_info(self):
        """
        Get information about all configurable parameters.
        
        Returns:
            Dictionary of parameter names and their specifications
        """
        return self.CONFIGURABLE_PARAMS
