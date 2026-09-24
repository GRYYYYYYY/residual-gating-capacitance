"""Cross-process conservative one-core wall-slot accounting with reservations."""
from contextlib import contextmanager
import fcntl,json,os,time,uuid
from pathlib import Path
from .common import ROOT


def authorization(kind,path=None):
    path=Path(path or ROOT/'configs/compute_authorization.json')
    if not path.exists():raise PermissionError('bulk compute allocation has not been approved')
    config=json.loads(path.read_text())
    if not config.get(f'bulk_{kind}_authorized',False):raise PermissionError(f'{kind} is not authorized')
    if not config.get('authorization_evidence'):raise PermissionError('user authorization evidence is required')
    limit=float(config['cpu_core_hours'])*3600
    if limit<=0:raise ValueError('positive CPU allocation required')
    return config,limit


class Ledger:
    def __init__(self,path,limit_seconds):
        self.path=Path(path);self.limit=limit_seconds;self.path.parent.mkdir(parents=True,exist_ok=True)
    def _update(self,fn):
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=json.loads(self.path.read_text()) if self.path.exists() else {'charged_seconds':0.,'reservations':{},'events':[]}
            result=fn(state)
            tmp=self.path.with_suffix(f'.{os.getpid()}.tmp');tmp.write_text(json.dumps(state,indent=2));os.replace(tmp,self.path)
            return result
    def reserve(self,label,seconds):
        if seconds<=0:raise ValueError('positive reservation required')
        def update(s):
            total=s['charged_seconds']+sum(v['seconds'] for v in s['reservations'].values())+seconds
            if total>self.limit:raise RuntimeError('compute allocation would be exceeded')
            token=uuid.uuid4().hex;s['reservations'][token]={'label':label,'seconds':seconds,'created_unix':time.time()}
            s['events'].append(dict(event='reserve',token=token,label=label,seconds=seconds));return token
        return self._update(update)
    def close(self,token,seconds,status):
        def update(s):
            reservation=s['reservations'].pop(token)
            if seconds<0:raise ValueError('negative charge')
            s['charged_seconds']+=seconds
            s['events'].append(dict(event='close',token=token,label=reservation['label'],seconds=seconds,status=status,
                                    reservation_overrun=max(0.,seconds-reservation['seconds'])))
        self._update(update)


@contextmanager
def allocation(kind,label,seconds):
    import signal
    config,limit=authorization(kind)
    ledger=Ledger(ROOT/'runs/compute_ledger.json',limit)
    token=ledger.reserve(label,seconds+10)
    start=time.perf_counter();status='failed'
    previous=signal.getsignal(signal.SIGALRM)
    def expired(signum,frame):raise TimeoutError('allocated compute slot expired')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,seconds)
    try:
        yield config
        status='completed'
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
        ledger.close(token,time.perf_counter()-start,status)
