from enum import Enum


class FAISSIndexType(str, Enum):
    L2 = "L2"
    INNER_PRODUCT = "InnerProduct"


class CacheType(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"


RATING_MIN = 1
RATING_MAX = 5
DEFAULT_TOP_K = 10
MAX_TOP_K = 100

TRAIN_SPLIT = 0.7
VAL_SPLIT = 0.15
TEST_SPLIT = 0.15

EMBEDDING_BATCH_SIZE = 100
EMBEDDING_MAX_RETRIES = 3

COLD_START_THRESHOLD = 5

