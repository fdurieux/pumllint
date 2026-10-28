import pickle
from pyarrow import Table


def write_table(table, where):
    with open(where, "wb") as fh:
        pickle.dump(table._df, fh)


def read_table(source, columns=None, partitioning="hive"):
    with open(source, "rb") as fh:
        df = pickle.load(fh)
    if columns is not None:
        df = df[list(columns)]
    return Table(df)
