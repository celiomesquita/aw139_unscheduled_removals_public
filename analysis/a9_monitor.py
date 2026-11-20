"""Sample parent/worker memory and CPU without changing their calculations."""
import threading

import psutil


class ResourceMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.cpu = {}
        self.peak_rss = 0
        self.workers = []
        self.thread = threading.Thread(target=self._run, daemon=True)

    def sample(self):
        records, rss, workers = {}, 0, []
        for process in [self.process, *self.process.children(recursive=True)]:
            try:
                times = process.cpu_times()
                records[(process.pid, process.create_time())] = times.user + times.system
                rss += process.memory_info().rss
                if process.pid != self.process.pid:
                    workers.append(process.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        with self.lock:
            for key, value in records.items():
                self.cpu[key] = max(self.cpu.get(key, 0.), value)
            self.peak_rss = max(self.peak_rss, rss)
            self.workers = sorted(workers)

    def _run(self):
        while not self.stop_event.wait(.5):
            self.sample()

    def start(self):
        self.sample()
        self.thread.start()

    def snapshot(self):
        with self.lock:
            return dict(aggregate_peak_rss_bytes_sampled=self.peak_rss,
                        cumulative_process_cpu_seconds_sampled=sum(self.cpu.values()),
                        live_worker_pids=list(self.workers),
                        cpu_scope='sampled process-lifetime lower bound; short exit gaps not imputed')

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=2)
        self.sample()
