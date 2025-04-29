class BetServiceError(Exception):
    """Base exception for bet service errors."""
    pass

class ValidationError(BetServiceError):
    """Exception raised for validation errors."""
    pass

class DatabaseError(BetServiceError):
    """Exception raised for database errors."""
    pass

class CacheError(BetServiceError):
    """Exception raised for cache errors."""
    pass

class AuthorizationError(BetServiceError):
    """Exception raised for authorization errors."""
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

class GameServiceError(Exception):
    """Base exception for game service errors."""
    pass

class APIError(GameServiceError):
    """Exception raised for API-related errors."""
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

class AnalyticsServiceError(Exception):
    """Base exception for analytics service errors."""
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