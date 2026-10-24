"""Run unchanged acceptance cases, optionally staging explicit external test doubles."""
import argparse,os,shlex,shutil,subprocess,sys,tempfile
from pathlib import Path
out=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--with-test-doubles',action='store_true',help='substitute only the missing shell externals; not a production external integration check')
p.add_argument('--independent',action='store_true',help='also run the additional independent checks')
a=p.parse_args()
env=dict(os.environ,JDL_ADAPTER='jdl_adapter',JDL_UNDER_TEST=f'{shlex.quote(sys.executable)} -m jef.data.cli',PYTHONPATH=str(out)+os.pathsep+os.environ.get('PYTHONPATH',''))
with tempfile.TemporaryDirectory(prefix='jef-chain-') as tmp:
 chain=out/'deploy/daily.sh'
 if a.with_test_doubles:
  chain=Path(tmp)/'daily.sh';shutil.copyfile(out/'deploy/daily.sh',chain);chain.chmod(0o755)
  for name in ['events.sh','dashboard.sh']:shutil.copyfile(out/'tests/externals'/name,Path(tmp)/name)
 env['JDL_CHAIN']=str(chain)
 paths=[str(out.parents[1]/'kit/features/steps')]
 if a.independent:paths.append(str(out/'tests/test_independent.py'))
 sys.exit(subprocess.call([sys.executable,'-m','pytest','-q',*paths],env=env))
