"""Constants used throughout the application."""

# Task Status Constants
STATUS_PENDING = "PENDING"
STATUS_STARTED = "STARTED"
STATUS_IN_PROGRESS = "PROGRESS"
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILURE = "FAILURE"
STATUS_FAILED = "FAILURE"  # Alias for FAILURE

# Task Queue Names
QUEUE_DEFAULT = "default"
QUEUE_ANALYSIS = "analysis"
QUEUE_BATCH_ANALYSIS = "batch_analysis"

# Cache Keys
CACHE_TASK_PREFIX = "task:game:"
CACHE_LOCK_PREFIX = "lock:game:"
CACHE_BATCH_PREFIX = "task:batch:"

# Time Constants (in seconds)
CACHE_TTL = 1800  # 30 minutes
LOCK_TTL = 300  # 5 minutes
TASK_EXPIRY = 3600  # 1 hour

# Analysis Constants
MAX_BATCH_SIZE = 50
DEFAULT_ANALYSIS_DEPTH = 20

# Credit System Constants
CREDIT_VALUES = {"basic": 10, "standard": 25, "premium": 50, "ultimate": 100}
