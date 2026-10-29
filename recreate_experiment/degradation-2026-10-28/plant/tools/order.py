"""The pre-registered selection order: ids by sha256("20261028:" + id), hex ascending."""
import hashlib, json, sys
reqs = json.load(open(sys.argv[1]))
ids = sorted((hashlib.sha256(f"20261028:{q['id']}".encode()).hexdigest(), q['id']) for q in reqs)
for rank, (h, i) in enumerate(ids, 1):
    print(rank, i, h[:12])
