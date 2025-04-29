class BotError(Exception):
    """Base exception class for all bot-related errors"""
    pass

class GameServiceError(BotError):
    """Exception raised for game service errors"""
    pass

class UserServiceError(BotError):
    """Exception raised for user service errors"""
    pass

class BetServiceError(BotError):
    """Exception raised for bet service errors"""
    pass

class ValidationError(BotError):
    """Exception raised for validation errors"""
    pass

class APIError(BotError):
    """Exception raised for API-related errors"""
    pass

class DatabaseError(BotError):
    """Exception raised for database-related errors"""
    pass

class CacheError(BotError):
    """Exception raised for cache-related errors"""
    pass

class ConfigurationError(BotError):
    """Exception raised for configuration errors"""
    pass

class PermissionError(BotError):
    """Exception raised for permission-related errors"""
    pass

class RateLimitError(BotError):
    """Exception raised for rate limit errors"""
    pass

class DatabaseConnectionError(DatabaseError):
    """Raised when there's an error connecting to the database"""
    pass

class DatabaseQueryError(DatabaseError):
    """Raised when there's an error executing a database query"""
    pass

class APIConnectionError(APIError):
    """Raised when there's an error connecting to an API"""
    pass

class APITimeoutError(APIError):
    """Raised when an API request times out"""
    pass

class APIResponseError(APIError):
    """Raised when there's an error in the API response"""
    pass

class VoiceServiceError(BotError):
    """Raised when there's an error in the voice service"""
    pass

class SportHandlerError(BotError):
    """Raised when there's an error in a sport handler"""
    pass 