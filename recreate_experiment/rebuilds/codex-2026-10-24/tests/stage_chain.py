"""Stage chain testing with explicit substitutes for absent supplied externals."""
from pathlib import Path
import shutil,sys
out=Path(__file__).resolve().parents[1]
target=Path(sys.argv[1]);target.mkdir(parents=True,exist_ok=True)
shutil.copyfile(out/'deploy/daily.sh',target/'daily.sh');(target/'daily.sh').chmod(0o755)
for name in ['events.sh','dashboard.sh']:shutil.copyfile(out/'tests/externals'/name,target/name)
print(target/'daily.sh')
