"""table_edit.py FEATURE DAY COLUMN NEWVALUE : replace the last cell of the one matching table row, keeping
the cell's width when the new value fits and overflowing it otherwise (the kit's own tables overflow)."""
import re, sys
def edit(path, day, column, new):
    text = open(path, encoding="utf-8").read()
    pat = re.compile(rf"^(\s*\|\s*{re.escape(day)}\s*\|\s*{re.escape(column)}\s*\|)( [^|]*)\|$", re.M)
    hits = pat.findall(text)
    assert len(hits) == 1, (path, day, column, len(hits))
    def repl(m):
        width = len(m.group(2)) - 1
        return m.group(1) + " " + new.ljust(width) + "|" if len(new) < width else m.group(1) + " " + new + " |"
    open(path, "w", encoding="utf-8").write(pat.sub(repl, text))
if __name__ == "__main__":
    edit(*sys.argv[1:5])
