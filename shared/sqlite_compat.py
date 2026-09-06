"""Use pysqlite3 when the system sqlite3 module is too old for SQLAlchemy."""

import sys

try:
    import pysqlite3

    sys.modules['sqlite3'] = pysqlite3
except ImportError:
    pass
