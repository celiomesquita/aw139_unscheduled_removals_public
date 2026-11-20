"""Read-only sampling of the unchanged reference evaluator's Python frames."""
import sys
import threading
import time
from pathlib import Path
from amendment015.state import OUT,atomic,utcnow


class ReadOnlyProgress:
    def __init__(self,item,interval=120.,path=None):
        self.item=item;self.interval=interval
        self.path=Path(path) if path else OUT/'fresh_progress'/f"{item['id']}.json"
        self.main_ident=threading.get_ident()
        self.total_phases=sum(len(c['daily'])*4 for c in item['contexts']
            if c['visits'] and any(v>0 for v in c['daily']))
        self.finished=threading.Event();self.last=None
        self.thread=threading.Thread(target=self._run,daemon=True)

    def snapshot(self):
        frame=sys._current_frames().get(self.main_ident)
        sweep=None;construct=None
        while frame is not None:
            filename=Path(frame.f_code.co_filename).name
            if filename=='a9_static.py' and frame.f_code.co_name=='exhaustive_threshold':
                sweep=frame.f_locals
            if filename in ('a9_static_fast.py','disk.py') and frame.f_code.co_name=='__init__':
                construct=frame.f_locals.get('self')
            frame=frame.f_back
        calendars=list(sweep.get('calendars',[])) if sweep is not None else []
        phases=sum(len(c.rows) for c in calendars)
        if construct is not None and not any(c is construct for c in calendars):
            # previous_stops is filled only after a phase's transition/cost row exists.
            phases+=len(getattr(construct,'previous_stops',{}))
        initialized=phases==self.total_phases and bool(calendars)
        total=sum(len(row['stops']) for c in calendars for row in c.rows) if initialized else None
        advanced=sum(min(row['cursor'],len(row['stops'])) for c in calendars for row in c.rows) if initialized else 0
        candidates=max(0,int(sweep.get('candidates',1))-1) if sweep is not None else 0
        observed=dict(id=self.item['id'],utc=utcnow().isoformat(),pid=__import__('os').getpid(),
            stage='breakpoint_sweep' if initialized else 'calendar_construction',
            phases_constructed=phases,phases_total=self.total_phases,
            phases_fraction=phases/self.total_phases if self.total_phases else None,
            phase_visit_breakpoints_advanced=advanced,phase_visit_breakpoints_total=total,
            breakpoints_fraction=advanced/total if total else None,
            distinct_candidate_points_evaluated=candidates,distinct_candidate_points_total=None,
            breakpoint_definition='visit breakpoints per phase, counted with multiplicity; advanced row cursors / all finite row stops',
            telemetry='read-only Python frame/counter sampling; no changes to evaluator objects, values or operation order')
        # When an evaluator frame has already returned, retain the last real sample.
        if sweep is not None:self.last=observed
        return self.last or observed

    def write(self):
        record=self.snapshot();atomic(self.path,record)
        with self.path.with_suffix('.jsonl').open('a') as f:f.write(__import__('json').dumps(record,sort_keys=True)+'\n')

    def _run(self):
        while not self.finished.wait(self.interval):self.write()

    def start(self):
        self.write();self.thread.start()

    def stop(self,complete=False):
        self.finished.set();self.thread.join(timeout=2)
        self.write()
        if complete:
            self.last=dict(self.last or self.snapshot(),stage='certified',utc=utcnow().isoformat(),
                phases_constructed=self.total_phases,phases_fraction=1.,breakpoints_fraction=1.)
            if self.last.get('phase_visit_breakpoints_total') is not None:
                self.last['phase_visit_breakpoints_advanced']=self.last['phase_visit_breakpoints_total']
            self.last['completion_source']='completed exact-reference certificate; sampled counters retained when totals were not yet observed'
            atomic(self.path,self.last)
