# Test-only stand-in for pyarrow (pickle-backed); never shipped.
__version__ = "0.0.1"
import pandas as _pd


class Table:
    def __init__(self, df):
        self._df = df

    @classmethod
    def from_pandas(cls, df, preserve_index=False):
        return cls(df.reset_index(drop=True).copy() if not preserve_index else df.copy())

    def to_pandas(self):
        return self._df.copy()


class Array:
    pass


class ChunkedArray:
    pass


class Scalar:
    pass
