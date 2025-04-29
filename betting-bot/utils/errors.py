class ServiceError(Exception):
    """Base class for all service-related errors."""
    pass

class BetServiceError(ServiceError):
    """Raised when there's an error in the bet service."""
    pass

class GameServiceError(ServiceError):
    """Raised when there's an error in the game service."""
    pass

class AnalyticsServiceError(ServiceError):
    """Raised when there's an error in the analytics service."""
    pass

class AdminServiceError(ServiceError):
    """Raised when there's an error in the admin service."""
    pass

class DataSyncError(ServiceError):
    """Raised when there's an error in data synchronization."""
    pass

class DatabaseError(Exception):
    """Raised when there's an error in database operations."""
    pass

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class AuthorizationError(Exception):
    """Raised when authorization fails."""
    pass

class RateLimitError(Exception):
    """Raised when rate limits are exceeded."""
    pass

class APIError(Exception):
    """Raised when there's an error in external API calls."""
    pass

class CacheError(Exception):
    """Raised when there's an error in cache operations."""
    pass

class ConfigurationError(Exception):
    """Raised when there's an error in configuration."""
    pass

class NotificationError(Exception):
    """Raised when there's an error in notification operations."""
    pass

class PaymentError(Exception):
    """Raised when there's an error in payment operations."""
    pass

class VoiceError(Exception):
    """Raised when there's an error in voice operations."""
    pass

class GameNotFoundError(BetServiceError):
    """Exception raised when a game is not found."""
    pass

class InsufficientUnitsError(BetServiceError):
    """Exception raised when a user has insufficient units."""
    pass

class InvalidBetTypeError(ValidationError):
    """Exception raised for invalid bet types."""
    pass

class InvalidOddsError(ValidationError):
    """Exception raised for invalid odds."""
    pass

class InvalidUnitsError(ValidationError):
    """Exception raised for invalid units."""
    pass

class GameDataError(GameServiceError):
    """Exception raised for game data errors."""
    pass

class LeagueNotFoundError(GameServiceError):
    """Exception raised when a league is not found."""
    pass

class ScheduleError(GameServiceError):
    """Exception raised for schedule-related errors."""
    pass

class StatsGenerationError(AnalyticsServiceError):
    """Exception raised for errors during stats generation."""
    pass

class DataProcessingError(AnalyticsServiceError):
    """Exception raised for errors during data processing."""
    pass

class VisualizationError(AnalyticsServiceError):
    """Exception raised for errors during data visualization."""
    pass 