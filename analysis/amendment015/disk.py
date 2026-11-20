"""Float64 storage-only adaptation of FastCalendarRenewal, with unchanged arithmetic."""
import json
import math
import mmap
from pathlib import Path
import tempfile
import time
import numpy as np
import psutil
from scipy.special import gamma,gammaincc
from a9_static_fast import FastCalendarRenewal,_kernel,_constant_kernel
from a9_static import exhaustive_threshold
from amendment015.state import OUT,ROOT,atomic,digest,freeze,check_deadline,utcnow

SCRATCH=OUT/'scratch'


class DiskCalendarRenewal(FastCalendarRenewal):
    def __init__(self,daily,visits,beta,eta,nu,r,weight=1.,subdivisions=1,
                 probability_tolerance=1e-10,duration_tolerance=1e-7):
        self.previous_stops={};self.previous_finite={};self.row_updates={}
        self.full_refactors=0;self.sparse_products=0
        self.daily=np.asarray(daily,float)
        self.n,self.step=len(daily)*subdivisions,1/subdivisions
        self.increment=np.repeat(self.daily/subdivisions,subdivisions)
        self.visits=np.array(sorted(set(int(v*subdivisions)%self.n for v in visits)),int)
        if (not len(self.visits) or self.n==0 or beta<=1 or eta<=0 or nu<0 or
            self.increment.min()<0 or self.increment.sum()<=0):
            raise ValueError('Static renewal calendar requires ageing, exposure and visits')
        self.beta,self.eta,self.nu,self.r,self.weight=beta,eta,nu,r,weight
        self.rows,self.kernel_kinds=[],{}
        self.P=np.zeros((self.n,self.n))
        self.cost,self.duration=np.zeros(self.n),np.zeros(self.n)
        self.mass_error,self.max_tail_probability,self.max_tail_duration=0.,0.,0.
        self.updates=0
        periods,total=1,self.increment.sum()
        while True:
            elapsed,exposure=periods*len(daily),periods*total
            probability=math.exp(-(exposure/eta)**beta-nu*elapsed)
            integrated=eta*gamma(1/beta)*gammaincc(1/beta,(exposure/eta)**beta)/beta
            duration_bound=probability/nu if nu else len(daily)*(probability+integrated/total)
            if probability<=probability_tolerance and duration_bound<=duration_tolerance:break
            periods*=2
            if periods>65536:raise ArithmeticError('Static calibration tail could not be bounded')
        self.max_tail_probability,self.max_tail_duration=probability,duration_bound
        constant=bool(np.all(self.increment==self.increment[0]))
        length=periods*self.n
        SCRATCH.mkdir(parents=True,exist_ok=True)
        self.folder=Path(tempfile.mkdtemp(prefix='calendar_',dir=SCRATCH))
        self.storage=np.memmap(self.folder/'kernels.float64',mode='w+',dtype=np.float64,
                              shape=(1 if constant else self.n,6,length+1))
        names=('clock','survival','left','right','reward','moment')
        for phase in range(self.n):
            check_deadline(references=True,refresh=False)
            kernel=(_constant_kernel(length,self.increment[0],beta,eta,nu,r,self.step)
                    if constant else _kernel(np.tile(np.roll(self.increment,-phase),periods),
                                            beta,eta,nu,r,self.step))
            if kernel['error']>1e-7:raise ArithmeticError('Static first-event quadrature does not conserve probability')
            self.mass_error=max(self.mass_error,kernel['error'])
            self.kernel_kinds[kernel['kind']]=self.kernel_kinds.get(kernel['kind'],0)+1
            offsets=np.arange((length+phase)//self.n+1)*self.n
            stops=(offsets[:,None]+self.visits[None,:]-phase).ravel()
            stops=stops[(stops>0)&(stops<=length)]
            row={}
            for column,name in enumerate(names):
                array=kernel[name]
                target=np.asarray(self.storage[0 if constant else phase,column,:len(array)])
                if not constant or phase==0:
                    np.copyto(target,array,casting='no')
                target.flags.writeable=False
                row[name]=target
            # No arithmetic is moved across this storage copy.
            self.storage.flush()
            del kernel
            row.update(phase=phase,stops=stops,cursor=0)
            self.rows.append(row)
            self.replace_row(phase,update_inverse=False)
        self.refactor()

    def replace_row(self,phase,update_inverse=True):
        super().replace_row(phase,update_inverse)
        if hasattr(self,'storage'):
            self.storage._mmap.madvise(mmap.MADV_DONTNEED)


def disk_threshold(contexts,beta,eta,nu,r,subdivisions=4):
    return exhaustive_threshold(contexts,beta,eta,nu,r,subdivisions,calendar_type=DiskCalendarRenewal)


def resource_estimate(item):
    """Same tail doubling as the historical estimator; keep dense algebra in RAM."""
    model=item['model'];beta,eta,nu=model['beta'],model['eta'],model['nu']
    disk=0;residual=0;max_length=0
    for context in item['contexts']:
        daily=np.asarray(context['daily'],float)
        if not context['visits'] or daily.sum()==0:continue
        period,total,repeats=len(daily),np.repeat(daily/4,4).sum(),1
        while True:
            exposure,elapsed=repeats*total,repeats*period
            probability=math.exp(-(exposure/eta)**beta-nu*elapsed)
            bound=probability/nu if nu else period*(probability+eta*gamma(1/beta)*gammaincc(1/beta,(exposure/eta)**beta)/beta/total)
            if probability<=1e-10 and bound<=1e-7:break
            repeats*=2
            if repeats>65536:raise ArithmeticError('Static calibration tail could not be bounded')
        n,length=period*4,period*4*repeats
        kernels=1 if np.all(daily==daily[0]) else n
        disk+=8*6*(length+1)*kernels
        residual+=8*(6*n*n+n*(repeats+1)*len(context['visits'])+80*(length+1))
        max_length=max(max_length,length)
    # Explicit reserve for imports, eight cached constant kernels and mapped pages.
    residual+=512*2**20+8*8*6*(max_length+1)+64*2**20
    return dict(residual_ram_estimated_bytes=int(residual),disk_estimated_bytes=int(disk),
                arithmetic='unchanged float64; only kernel storage moved to memmap',subdivisions=4)


def disk_job(item):
    check_deadline(references=True,refresh=False)
    gate=json.loads((OUT/'disk_ready.json').read_text())
    for path,h in gate['sources'].items():
        if digest(ROOT/path)!=h:raise RuntimeError('DISK_SOURCE_CHANGED')
    name=item['id'];checkpoint=OUT/'references'/f'{name}_checkpoint.json'
    before=json.loads(checkpoint.read_text());before.update(status='running',storage='memmap',started_utc=utcnow().isoformat())
    atomic(checkpoint,before)
    wall,cpu=time.perf_counter(),time.process_time();m=item['model']
    age,diagnostics=disk_threshold(item['contexts'],m['beta'],m['eta'],m['nu'],item['r'],4)
    check_deadline(references=True,refresh=False)
    rate=diagnostics.get('expected_rate_variable_groups')
    if not diagnostics.get('global_discrete_search') or rate is None or not math.isfinite(rate):raise ArithmeticError('EXACT_REFERENCE_NOT_CERTIFIED')
    certificate=dict(id=name,pn=item['pn'],r=item['r'],status='complete',
        input_sha256=digest(OUT/'references'/f'{name}_inputs.json'),subdivisions=4,
        configuration_sha256=digest(OUT/'configuration.json'),
        evaluator_sha256={p:digest(ROOT/p) for p in ('analysis/a9_static.py','analysis/a9_static_fast.py')},
        storage_source_sha256=digest(__file__),equivalence_sha256=digest(OUT/'disk_equivalence.json'),
        age=None if math.isinf(age) else age,infinite=math.isinf(age),rate=rate,
        diagnostics=diagnostics,wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
        final_rss_bytes=psutil.Process().memory_info().rss)
    path=OUT/'references'/f'{name}_certificate.json';freeze(path,certificate)
    before.update(status='complete',certificate=path.name,certificate_sha256=digest(path));atomic(checkpoint,before)
    return name
