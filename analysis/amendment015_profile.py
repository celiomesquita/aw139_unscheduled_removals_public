"""One T20 timing replica only; no effects or detection records are persisted."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import time
PROCESS_START=time.perf_counter()
import contextlib
from collections import Counter
import json
import signal
import threading
import traceback
from unittest.mock import patch
import pandas as pd
import psutil
from a16_generator import load_design,START
from a9_environment import Environment,historical_calendars
from a9_fitting import fit_observable
from a9_warmup import SharedWarmup,generate,POLICIES
import a9_simulation as simulation
import a9_planning as planning
from a9_monitor import ResourceMonitor
from amendment015.execution import AgeCalibrationExecutor
from amendment015.age import require_manifest
from amendment015.references import check_sources
from amendment015.state import ROOT,OUT,atomic,digest,freeze,ledger,check_deadline,utcnow

PROFILE=OUT/'profile'
CELL=dict(index=71,level='amplified',knowledge='realized_fh',r=10,scenario='B-gradual')
# Dedicated profiling key outside pilot indices 0..4 and main indices 0..199.
REPLICATE=5


class Timing:
    def __init__(self,allocation):
        self.allocation=allocation
        self.policy=None;self.month=None;self.origin=None;self.events=[];self.months=[]
        self.month_start=None;self.month_event_start=0;self.monitor=ResourceMonitor()
        self.month_cpu_start=0.
        self.resource_state=dict(processes={},peak_rss_by_pid={})
        self.monitor.start();self.issue=None;self.done=threading.Event()
        self.watcher=threading.Thread(target=self.watch,daemon=True);self.watcher.start()
        self.write_wall=0.

    def watch(self):
        peaks={}
        while not self.done.wait(1.):
            self.monitor.sample()
            processes=[psutil.Process()]+psutil.Process().children(recursive=True)
            records={}
            for p in processes:
                try:
                    t=p.cpu_times();records[str(p.pid)]=dict(rss=p.memory_info().rss,cpu_user_system=t.user+t.system)
                except psutil.NoSuchProcess:pass
            for pid,record in records.items():peaks[pid]=max(peaks.get(pid,0),record['rss'])
            self.resource_state=dict(utc=utcnow().isoformat(),policy=self.policy,month=self.month,
                processes=records,peak_rss_by_pid=dict(peaks),
                aggregate_rss_bytes=sum(x['rss'] for x in records.values()),python_processes=len(records))
            atomic(PROFILE/'resources_latest.json',self.resource_state)
            with (PROFILE/'resources.jsonl').open('a') as f:
                f.write(json.dumps(self.resource_state,sort_keys=True)+'\n');f.flush()
            if len(records)>8:self.issue='MORE_THAN_EIGHT_EXECUTOR_PROCESSES'
            if sum(x['rss'] for x in records.values())>self.allocation:self.issue='FROZEN_MEMORY_ALLOCATION_EXCEEDED'
            if self.issue:os.kill(os.getpid(),signal.SIGTERM);return

    def write(self,path,value):
        before=time.perf_counter();atomic(path,value);self.write_wall+=time.perf_counter()-before

    @contextlib.contextmanager
    def stage(self,name):
        wall,cpu=time.perf_counter(),time.process_time()
        policy,month,origin=self.policy,self.month,self.origin
        try:yield
        finally:
            row=dict(stage=name,policy=policy,month=month,origin=origin,
                wall_seconds=time.perf_counter()-wall,coordinator_cpu_user_system_seconds=time.process_time()-cpu,
                utc=utcnow().isoformat(),rss_snapshot_by_pid=self.resource_state['processes'],
                peak_rss_by_pid_sampled=self.resource_state['peak_rss_by_pid'],**self.monitor.snapshot())
            self.events.append(row)
            before=time.perf_counter()
            with (PROFILE/'stages.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
            self.write_wall+=time.perf_counter()-before

    def timed(self,name,function):
        def wrapped(*args,**kwargs):
            with self.stage(name):return function(*args,**kwargs)
        return wrapped

    def close_month(self):
        if self.month_start is None:return
        wall=time.perf_counter()-self.month_start
        rows=self.events[self.month_event_start:]
        exclusive=sum(x['wall_seconds'] for x in rows if x['stage'] in ('A4_fit','age_calibration','planning'))
        self.months.append(dict(policy=self.policy,month=self.month,origin=self.origin,
            wall_seconds=wall,simulation_and_recording_residual_seconds=wall-exclusive,
            stage_counts=dict(Counter(x['stage'] for x in rows)),
            cpu_user_system_interval_seconds_sampled=self.monitor.snapshot()['cumulative_process_cpu_seconds_sampled']-self.month_cpu_start,
            rss_snapshot_by_pid=self.resource_state['processes'],
            peak_rss_by_pid_sampled=self.resource_state['peak_rss_by_pid'],
            decomposition='month total minus A4, calibration, planning; nested MILP not subtracted twice'))
        self.write(PROFILE/'months.json',self.months)
        self.month_start=None

    def heartbeat(self,**fields):
        check_deadline()
        if self.issue:raise RuntimeError(self.issue)
        if fields.get('stage')=='policy':
            self.close_month();self.policy=fields['policy'];self.month=fields['month'];self.origin=fields['origin']
            self.month_start=time.perf_counter();self.month_event_start=len(self.events)
            self.month_cpu_start=self.monitor.snapshot()['cumulative_process_cpu_seconds_sampled']
        self.write(PROFILE/'progress.json',dict(fields,utc=utcnow().isoformat(),
            elapsed_wall_seconds=time.perf_counter()-PROCESS_START,**self.monitor.snapshot()))

    def stop(self):
        self.done.set();self.watcher.join(timeout=2);self.monitor.stop()


def run():
    PROFILE.mkdir(parents=True,exist_ok=True)
    if (PROFILE/'state.json').exists():raise RuntimeError('PRESERVED_PROFILE_REPLICA_REQUIRES_REVIEW_BEFORE_REEXECUTION')
    require_manifest(OUT/'references/manifest.json')
    verified=json.loads((OUT/'verification_manifest.json').read_text())
    if verified['status']!='passed' or verified['N']!=9:raise RuntimeError('NINE_CASE_VERIFICATION_NOT_PASSED')
    config=json.loads((OUT/'configuration.json').read_text());check_sources(config)
    paths=[ROOT/'analysis/amendment015_profile.py',ROOT/'analysis/amendment015/execution.py']
    inputs=['config/a4_scale_map.csv','data/anonymised/hours_flown.csv','data/derived/stoppages.csv','data/derived/a9/resources/preventive_mh.csv']
    specification=dict(cell=CELL,replicate=REPLICATE,phase='pilot',profile_only=True,
        pilot_indices_still_pending=list(range(5)),main_R=200,main_cells=72,policies=list(POLICIES),
        workers=6,native_threads=1,cbc_threads=1,watchdog_seconds=10800,
        memory_allocation_bytes=config['memory_budget_bytes'],sources={str(p.relative_to(ROOT)):digest(p) for p in paths},
        inputs={p:digest(ROOT/p) for p in inputs},reference_manifest_sha256=digest(OUT/'references/manifest.json'),
        verification_manifest_sha256=digest(OUT/'verification_manifest.json'),
        time_convention='monotonic wall includes imports/loading/warmup/fit/calibration/wait/MILP/simulation/writes; CPU user+system per distinct PID reported separately, never added to wall',
        effects_or_alarms_opened=False,inference=False)
    freeze(PROFILE/'configuration.json',specification)
    ledger('T20_profile')
    timing=Timing(config['memory_budget_bytes'])
    def expired(signum,frame):raise TimeoutError(timing.issue or 'T20_THREE_HOUR_WATCHDOG_OR_GLOBAL_DEADLINE')
    signal.signal(signal.SIGTERM,expired);signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,min(max(.001,10800-(time.perf_counter()-PROCESS_START)),check_deadline()['remaining_seconds']))
    atomic(PROFILE/'state.json',dict(status='running',pid=os.getpid(),started_utc=utcnow().isoformat()))
    try:
        with timing.stage('loading'):
            truth,_,_,channels,_,_=load_design()
            domain=pd.read_csv(ROOT/'config/a4_scale_map.csv')
            flights=pd.read_csv(ROOT/'data/anonymised/hours_flown.csv')
            stops=pd.read_csv(ROOT/'data/derived/stoppages.csv')
            resources=pd.read_csv(ROOT/'data/derived/a9/resources/preventive_mh.csv').set_index('pn').principal_mh.to_dict()
        with timing.stage('auxiliary_generation_and_writing'):
            folder=PROFILE/'warmup';folder.mkdir(parents=True,exist_ok=True)
            spells,clocks,metadata=generate(REPLICATE,CELL['level'],'pilot',truth,channels,flights)
            spells.to_csv(folder/'spells.csv',index=False);clocks.to_csv(folder/'flights.csv',index=False)
            atomic(folder/'manifest.json',dict(**metadata,outputs={name:digest(folder/name) for name in ['spells.csv','flights.csv']}))
            shared=SharedWarmup(folder)
        with timing.stage('initial_A4_fit'):
            initial_spells,initial_clocks=shared.for_policy('P0')
            initial,metadata=fit_observable(initial_spells,initial_clocks,domain,START)
        with timing.stage('historical_calendars'):
            contexts,utilisation=historical_calendars(initial_spells,initial_clocks,stops,domain,START)
            environment=Environment(flights,stops,CELL['scenario'])
        with AgeCalibrationExecutor(6) as executor:
            original_calibrate=executor.calibrate
            executor.calibrate=timing.timed('age_calibration',original_calibrate)
            thresholds,_=executor.calibrate(initial,contexts,CELL['r'],timing.heartbeat)
            with patch.object(simulation,'planned_actions',timing.timed('planning',simulation.planned_actions)),patch.object(planning,'solve_paths',timing.timed('MILP',planning.solve_paths)):
                for policy in POLICIES:
                    timing.policy=policy;timing.month=None;timing.origin=None
                    with timing.stage('complete_policy'):
                        result=simulation.simulate_policy(policy,CELL,REPLICATE,'pilot',shared,initial,thresholds,
                            contexts,utilisation,truth,channels,domain,environment,resources,timing.heartbeat,
                            refit=timing.timed('A4_fit',fit_observable),calibration_executor=executor)
                        # Do not read any financial/detection field. Discard the entire policy result.
                        del result
                        timing.close_month()
            timing.write(PROFILE/'calibration_worker_timings.json',executor.timings)
        with timing.stage('closing_integrity'):
            check_sources(config);require_manifest(OUT/'references/manifest.json')
            for path,h in specification['inputs'].items():
                if digest(ROOT/path)!=h:raise RuntimeError('PROFILE_INPUT_CHANGED')
        timing.write(PROFILE/'state.json',dict(status='complete',complete_policies=6,replicate=REPLICATE,
            cell=71,main_executed=False,technical_pilot_executed=False,effects_or_alarms_opened=False,
            stage_records=len(timing.events),months=len(timing.months),recording_wall_seconds=timing.write_wall,
            **timing.monitor.snapshot()))
        elapsed=time.perf_counter()-PROCESS_START
        freeze(PROFILE/'manifest.json',dict(status='complete',t71_seconds=elapsed,complete_policies=6,
            stage_counts=dict(Counter(row['stage'] for row in timing.events)),
            configuration_sha256=digest(PROFILE/'configuration.json'),stage_records_sha256=digest(PROFILE/'stages.jsonl'),
            months_sha256=digest(PROFILE/'months.json'),effects_or_alarms_opened=False,profile_outside_R=True))
        ledger('T20_complete_STOP')
    except BaseException as error:
        timing.close_month()
        atomic(PROFILE/'failure.json',dict(error=type(error).__name__,message=str(error),traceback=traceback.format_exc(),
            elapsed_seconds=time.perf_counter()-PROCESS_START,**timing.monitor.snapshot()))
        atomic(PROFILE/'state.json',dict(status='STOP_incomplete',error=type(error).__name__,elapsed_seconds=time.perf_counter()-PROCESS_START))
        ledger('technical_stop',stop=dict(code=type(error).__name__,message=str(error)))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);timing.stop()

if __name__=='__main__':run()
