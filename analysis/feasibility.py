"""Feasibility study on the anonymised AW139 fleet data.

1. Clean removals.csv.
2. Build an aircraft flight-hour clock (hours_flown cumulated, anchored to OMTH aircraft hours).
3. Build installation spells per P/N (left-truncated, right-censored) and fit Weibull by MLE.
4. Identify recurrent tasks and recurrent maintenance stoppages per aircraft in OMTH.

Outputs go to data/derived/ (anonymised IDs only, no free text) and analysis/feasibility_report.md.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "solver"))
from paths import ANONYMISED, ROOT  # noqa: E402

DERIVED = ROOT / "data" / "derived"
REPORT = ROOT / "analysis" / "feasibility_report.md"
START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2026-03-31")

MATCH_DAYS = 3          # tolerance to match a replacement install to a later removal
MIN_EVENTS = 5          # minimum failures to fit a Weibull per P/N
PERIODIC_CV = 0.30      # max coefficient of variation of the interval for a periodic task
MIN_INTERVALS = 10      # min observed intervals (fleet) for a task to be classified
STOP_MIN_FH = 100       # periodic tasks with interval >= this (FH) ...
STOP_MIN_DAYS = 90      # ... or >= this (days) define a maintenance stoppage
STOP_GAP_DAYS = 2       # stop days closer than this are merged into one stoppage

np.random.seed(0)
sys.stdout.reconfigure(encoding="utf-8")
report = []


def say(line=""):
    report.append(line)
    print(line)


# ----------------------------------------------------------------------------- 1. removals
def load_removals():
    r = pd.read_csv(ANONYMISED / "removals.csv", low_memory=False)
    n_raw = len(r)
    r = r[r["Part #"].notna()].copy()
    n_blank = n_raw - len(r)
    n_dup = r.drop(columns=["RowIndentity"]).duplicated().sum()
    r = r.drop(columns=["RowIndentity"]).drop_duplicates()

    r["att"] = pd.to_datetime(r["Attached Date"], format="%d/%m/%Y %H:%M", errors="coerce").dt.normalize()
    r["rem"] = pd.to_datetime(r["Removed Date"], format="%d/%m/%Y %H:%M", errors="coerce").dt.normalize()
    r["event"] = (r["Reason Category"] == "UNSCHEDULED").astype(int)
    r["tracked"] = r["Removal Type"] == "Tracked"
    days_chk = ((r["rem"] - r["att"]).dt.days - r["Days On A/c"]).abs()

    say("## 1. removals.csv cleaning")
    say(f"- Raw rows: {n_raw}; empty rows (only column `I`): {n_blank}; exact duplicates removed: {n_dup}; kept: {len(r)}.")
    say(f"- Removal dates: {r.rem.min().date()} to {r.rem.max().date()}; unparsed: {r.rem.isna().sum()}.")
    say(f"- Tracked: {r.tracked.sum()} (attach date present in {r.loc[r.tracked, 'att'].notna().mean():.1%}); "
        f"non-tracked: {(~r.tracked).sum()} (no attach date: survival not identifiable, only event counts).")
    say(f"- `Days On A/c` present in {r['Days On A/c'].notna().mean():.1%} of rows; where present, it agrees with "
        f"attach/remove dates within 1 day in {(days_chk.dropna() <= 1).mean():.1%}.")
    say("")
    say("Reason code by category (event = UNSCHEDULED; all other removals censor the spell):")
    say("")
    ct = pd.crosstab(r["Reason Code"], r["Reason Category"])
    say(ct.to_markdown())
    say("")
    cov = {c: r[c].notna().mean() for c in ["Std Cost", "Repair Cost", "Source Doc #", "ATA #"]}
    say("Field coverage: " + "; ".join(f"`{k}` {v:.1%}" for k, v in cov.items()) + ".")
    say("")
    return r


# ----------------------------------------------------------------------------- 2. FH clock
def build_clock(omth):
    h = pd.read_csv(ANONYMISED / "hours_flown.csv")
    h["d"] = pd.to_datetime(h["Flight Date"], format="%d/%m/%Y")
    h["Hours"] = h["Hours"].fillna(0.0)
    days = pd.date_range(START, END, freq="D")
    daily = (h.groupby(["Aircraft #", "d"])["Hours"].sum()
               .unstack(0).reindex(days).fillna(0.0))
    cum = daily.cumsum()

    o = omth.dropna(subset=["d", "Aircraft Hours"])
    o = o[(o.d >= START) & (o.d <= END)]
    rows = []
    for ac, g in o.groupby("Aircraft #"):
        c = cum[ac].reindex(g.d).to_numpy()
        diff = g["Aircraft Hours"].to_numpy() - c
        off = np.median(diff)
        mad = np.median(np.abs(diff - off))
        rows.append((ac, off, mad, len(g), np.mean(np.abs(diff - off) > 10)))
    anchor = pd.DataFrame(rows, columns=["ac", "offset", "mad", "n", "outlier_share"]).set_index("ac")
    clock = cum + anchor["offset"]
    rate = daily.sum() / len(days)

    say("## 2. Aircraft flight-hour clock")
    say(f"- FH(ac, day) = OMTH-anchored offset + cumulative `hours_flown`; {daily.shape[1]} aircraft, "
        f"{daily.to_numpy().sum():,.0f} FH, mean utilisation {rate.mean() * 365:,.0f} FH/aircraft/year.")
    say(f"- Anchor residual (|OMTH hours - clock|): median MAD {anchor.mad.median():.1f} FH, worst aircraft "
        f"{anchor.mad.max():.1f} FH; OMTH rows > 10 FH off the clock: {np.average(anchor.outlier_share, weights=anchor.n):.1%}.")
    say("- Before 2024-01-01 the clock is extrapolated backwards at each aircraft's mean utilisation (flagged `fh_est`).")
    say("")
    return clock, rate, anchor


def fh_at(clock, rate, ac, d):
    """Aircraft FH at date d; backward linear extrapolation before START."""
    if pd.isna(d) or ac not in clock:
        return np.nan
    if d < START:
        return clock[ac].iloc[0] - rate[ac] * (START - d).days
    return clock[ac].iloc[min((d - START).days, len(clock) - 1)]


# ----------------------------------------------------------------------------- 3. spells + Weibull
def build_spells(r, clock, rate):
    tr = r[r.tracked & r.att.notna()].copy()
    removed = tr[["Part #", "Part Description", "Serial #", "Aircraft #", "ATA #", "att", "rem", "event", "Reason Code"]].rename(
        columns={"Part Description": "desc"}).copy()
    removed["source"] = np.where(removed.att >= START, "in_window_removed", "pre_window_removed")

    # replacement installs: the unit fitted at a tracked removal starts a spell on the removal date
    inst = tr.dropna(subset=["Attached Serial #", "Attached Part #"])
    inst = inst[["Attached Part #", "Att. Part Description", "Attached Serial #", "Aircraft #", "ATA #", "rem"]].rename(
        columns={"Attached Part #": "Part #", "Att. Part Description": "desc", "Attached Serial #": "Serial #", "rem": "att"})
    inst = inst.drop_duplicates()
    m = inst.reset_index().merge(removed[["Part #", "Serial #", "Aircraft #", "att"]].rename(columns={"att": "att_r"}),
                                 on=["Part #", "Serial #", "Aircraft #"], how="left")
    m["hit"] = (m.att_r - m.att).abs().dt.days <= MATCH_DAYS
    matched = m.groupby("index")["hit"].any()
    inst["matched"] = matched.reindex(inst.index).fillna(False).to_numpy()
    cens = inst[~inst.matched].copy()
    cens["rem"], cens["event"], cens["Reason Code"], cens["source"] = END, 0, "IN_SERVICE", "in_window_censored"

    sp = pd.concat([removed, cens.drop(columns="matched")], ignore_index=True)
    n_noac = sp["Aircraft #"].isna().sum()
    sp = sp[sp["Aircraft #"].notna()].copy()
    sp["fh_att"] = [fh_at(clock, rate, a, d) for a, d in zip(sp["Aircraft #"], sp.att)]
    sp["fh_rem"] = [fh_at(clock, rate, a, d) for a, d in zip(sp["Aircraft #"], sp.rem)]
    sp["fh_start"] = [fh_at(clock, rate, a, START) for a in sp["Aircraft #"]]
    sp["fh_est"] = sp.att < START
    sp["t_fh"] = (sp.fh_rem - sp.fh_att).clip(lower=0.1)
    sp["entry_fh"] = np.where(sp.att < START, (sp.fh_start - sp.fh_att).clip(lower=0), 0.0)
    sp["t_days"] = (sp.rem - sp.att).dt.days.clip(lower=1)

    in_win_rem = (removed.source == "in_window_removed").sum()
    say("## 3. Installation spells per P/N")
    say(f"- Tracked spells with attach date: {len(removed)} removed spells "
        f"({in_win_rem} installed inside the window, {len(removed) - in_win_rem} before it).")
    say(f"- Replacement installs at tracked removals: {len(inst)}; matched to a later removal within "
        f"±{MATCH_DAYS} d: {inst.matched.sum()} ({inst.matched.mean():.1%}); unmatched, censored at "
        f"{END.date()}: {len(cens)}.")
    say(f"- Consistency check: {in_win_rem} in-window removed spells vs {inst.matched.sum()} matched installs "
        f"(in-window installs not preceded by a recorded removal cannot be seen).")
    say(f"- Spells without aircraft (removed from a parent assembly off-aircraft, no FH clock): {n_noac}, dropped.")
    say("- **Selection bias.** Units fitted before 2024 and still fitted in March 2026 are absent from the data, "
        "so pre-window spells are observed only if they were removed. Using them with left truncation alone "
        "under-represents long lives. The primary cohort is therefore the in-window installs "
        "(removed or censored); pre-window spells are kept for sensitivity only.")
    say("")
    return sp


def weibull_fit(t, d, e):
    """MLE of Weibull (beta, eta) with right censoring and left truncation; returns beta, eta, beta 95% CI."""
    t, d, e = map(np.asarray, (t, d, e))
    s = np.median(t)
    t, e = t / s, e / s

    def nll(p):
        b, k = np.exp(p)
        return -(np.sum(d * (np.log(b) - b * np.log(k) + (b - 1) * np.log(t)))
                 - np.sum((t / k) ** b) + np.sum((e / k) ** b))

    res = minimize(nll, x0=[0.0, 0.0], method="Nelder-Mead", options=dict(xatol=1e-8, fatol=1e-10, maxiter=5000))
    b, k = np.exp(res.x)
    h, H = 1e-4, np.zeros((2, 2))  # numerical Hessian of the NLL in (log beta, log eta)
    for i in range(2):
        for j in range(2):
            ei, ej = np.eye(2)[i] * h, np.eye(2)[j] * h
            H[i, j] = (nll(res.x + ei + ej) - nll(res.x + ei - ej) - nll(res.x - ei + ej) + nll(res.x - ei - ej)) / (4 * h * h)
    try:
        se = np.sqrt(np.linalg.inv(H)[0, 0])
    except np.linalg.LinAlgError:
        se = np.nan
    return b, k * s, b * np.exp(-1.96 * se), b * np.exp(1.96 * se), bool(res.success)


def fit_by_pn(sp, cohort):
    rows = []
    for pn, g in sp[sp.source.isin(cohort)].groupby("Part #"):
        n_ev = int(g.event.sum())
        if n_ev < MIN_EVENTS:
            continue
        b, eta, lo, hi, ok = weibull_fit(g.t_fh, g.event, g.entry_fh)
        rows.append(dict(pn=pn, desc=g["desc"].mode().iat[0], ata=g["ATA #"].mode().iat[0] if g["ATA #"].notna().any() else np.nan,
                         spells=len(g), events=n_ev, censored=len(g) - n_ev, beta=b, beta_lo=lo, beta_hi=hi,
                         eta_fh=eta, converged=ok,
                         regime="wear-out" if lo > 1 else ("infant/random" if hi < 1 else "undetermined")))
    return pd.DataFrame(rows).sort_values("events", ascending=False)


# ----------------------------------------------------------------------------- 4. OMTH
def load_omth():
    t = pd.read_csv(ANONYMISED / "OMTH_tasks.csv", low_memory=False)
    t["d"] = pd.to_datetime(t["Tech Sign Off Date"], format="%m/%d/%Y", errors="coerce")
    miss = t.d.isna().sum()
    doc_date = t.dropna(subset=["d"]).groupby("Execution Doc #")["d"].median()
    t.loc[t.d.isna(), "d"] = t.loc[t.d.isna(), "Execution Doc #"].map(doc_date)
    t["d"] = t.d.dt.normalize()
    t["nst"] = t["Task #"].astype(str).str.contains("NST")
    out = t[(t.d < START) | (t.d > END)]
    say("## 4. OMTH tasks")
    say(f"- Rows: {len(t)}; `Tech Sign Off Date` is month-first (MM/DD/YYYY), unlike the day-first dates of the "
        f"other two files. Missing dates: {miss}, of which {miss - t.d.isna().sum()} recovered from the "
        f"execution document; still missing: {t.d.isna().sum()}.")
    say(f"- Rows dated after {END.date()}: {(t.d > END).sum()} (outside the flight-hour window, excluded from FH metrics).")
    say(f"- Non-scheduled (`NST`) rows: {t.nst.mean():.1%}; man-hours present: {t['Tot Man Hours'].notna().mean():.1%}; "
        f"total {t['Tot Man Hours'].sum():,.0f} MH.")
    say("")
    return t[~t.index.isin(out.index) | t.d.isna()]


def recurrent_tasks(t, clock):
    s = t[~t.nst & t.d.notna() & (t.d <= END)].copy()
    s = (s.groupby(["Aircraft #", "Task #", "d"], as_index=False)
           .agg(mh=("Tot Man Hours", "sum")))
    s["fh"] = [clock[a].iloc[(d - START).days] if a in clock else np.nan for a, d in zip(s["Aircraft #"], s.d)]
    s = s.sort_values(["Aircraft #", "Task #", "d"])
    g = s.groupby(["Aircraft #", "Task #"])
    s["dfh"], s["ddays"] = g.fh.diff(), g.d.diff().dt.days
    iv = s.dropna(subset=["ddays"])
    iv = iv[iv.ddays > 0]

    def cv(x):
        return x.std() / x.mean() if x.mean() > 0 else np.nan

    agg = iv.groupby("Task #").agg(intervals=("ddays", "size"), aircraft=("Aircraft #", "nunique"),
                                   med_fh=("dfh", "median"), cv_fh=("dfh", cv),
                                   med_days=("ddays", "median"), cv_days=("ddays", cv))
    mh = s.groupby("Task #").mh.median().rename("med_mh")
    agg = agg.join(mh)
    agg = agg[agg.intervals >= MIN_INTERVALS]
    agg["driver"] = np.where(agg.cv_fh < agg.cv_days, "FH", "calendar")
    agg["cv_min"] = agg[["cv_fh", "cv_days"]].min(axis=1)
    agg["periodic"] = agg.cv_min <= PERIODIC_CV
    agg = agg.sort_values("intervals", ascending=False)

    per = agg[agg.periodic]
    say("## 5. Recurrent (periodic) tasks")
    say(f"- Scheduled task codes with ≥ {MIN_INTERVALS} fleet intervals: {len(agg)}; periodic "
        f"(CV of interval ≤ {PERIODIC_CV}): {len(per)} ({(per.driver == 'FH').sum()} FH-driven, "
        f"{(per.driver == 'calendar').sum()} calendar-driven).")
    say("")
    say("Most frequent periodic tasks:")
    say("")
    show = per.head(15)[["intervals", "aircraft", "driver", "med_fh", "cv_fh", "med_days", "cv_days", "med_mh"]]
    say(show.round(2).to_markdown())
    say("")
    return agg, s


def stoppages(s, agg, r, clock):
    per = agg[agg.periodic]
    long_tasks = per[((per.driver == "FH") & (per.med_fh >= STOP_MIN_FH)) |
                     ((per.driver == "calendar") & (per.med_days >= STOP_MIN_DAYS))].index
    days = s[s["Task #"].isin(long_tasks)].groupby(["Aircraft #", "d"]).agg(
        n_tasks=("Task #", "nunique"), mh=("mh", "sum")).reset_index()
    days = days.sort_values(["Aircraft #", "d"])
    days["new"] = days.groupby("Aircraft #").d.diff().dt.days.fillna(999) > STOP_GAP_DAYS
    days["stop_id"] = days.groupby("Aircraft #").new.cumsum()
    st = days.groupby(["Aircraft #", "stop_id"]).agg(start=("d", "min"), end=("d", "max"),
                                                     n_tasks=("n_tasks", "sum"), mh=("mh", "sum")).reset_index()
    st["fh"] = [clock[a].iloc[(d - START).days] for a, d in zip(st["Aircraft #"], st.start)]
    st["gap_fh"] = st.groupby("Aircraft #").fh.diff()
    st["gap_days"] = st.groupby("Aircraft #").start.diff().dt.days
    st["dur_days"] = (st.end - st.start).dt.days + 1

    # opportunity: unscheduled removals that coincide with a stoppage
    u = r[(r.event == 1) & r.rem.notna()][["Aircraft #", "rem"]]
    hit = []
    for ac, g in u.groupby("Aircraft #"):
        w = st[st["Aircraft #"] == ac]
        for d in g.rem:
            hit.append(((w.start - pd.Timedelta(days=STOP_GAP_DAYS) <= d) &
                        (d <= w.end + pd.Timedelta(days=STOP_GAP_DAYS))).any())
    per_ac = st.groupby("Aircraft #").size()

    say("## 6. Recurrent maintenance stoppages per aircraft")
    say(f"- Stoppage = run of days (gaps ≤ {STOP_GAP_DAYS} d) with at least one periodic task of interval "
        f"≥ {STOP_MIN_FH} FH (FH-driven) or ≥ {STOP_MIN_DAYS} d (calendar-driven); {len(long_tasks)} task codes qualify.")
    say(f"- Stoppages: {len(st)} ({per_ac.min()}–{per_ac.max()} per aircraft, median {per_ac.median():.0f}).")
    say(f"- Spacing: median {st.gap_fh.median():.0f} FH (IQR {st.gap_fh.quantile(.25):.0f}–{st.gap_fh.quantile(.75):.0f}), "
        f"median {st.gap_days.median():.0f} d; duration median {st.dur_days.median():.0f} d; "
        f"median {st.mh.median():.0f} MH of the qualifying tasks per stoppage.")
    say(f"- Unscheduled removals falling inside a stoppage (±{STOP_GAP_DAYS} d): {np.mean(hit):.1%} of {len(hit)}.")
    say("")
    return st, long_tasks


def main():
    DERIVED.mkdir(exist_ok=True)
    say("# Feasibility report — anonymised AW139 fleet data")
    say("")
    say("Generated by `analysis/feasibility.py`. Window: 2024-01-01 to 2026-03-31.")
    say("")
    r = load_removals()
    omth = load_omth()
    say(f"Removals linked to an OMTH execution document (`Source Doc #` = `Execution Doc #`): "
        f"{r['Source Doc #'].isin(omth['Execution Doc #']).mean():.1%}.")
    say("")
    clock, rate, anchor = build_clock(omth)
    sp = build_spells(r, clock, rate)

    prim = fit_by_pn(sp, ["in_window_removed", "in_window_censored"])
    sens = fit_by_pn(sp, ["in_window_removed", "in_window_censored", "pre_window_removed"])
    say("### Weibull per P/N (FH time scale, MLE with censoring and left truncation)")
    say(f"- Primary cohort (in-window installs): {len(prim)} P/N with ≥ {MIN_EVENTS} failures; regime by 95% CI of β: "
        + ", ".join(f"{k} {v}" for k, v in prim.regime.value_counts().items()) + ".")
    say(f"- Sensitivity (adding pre-window removed spells): {len(sens)} P/N; "
        + ", ".join(f"{k} {v}" for k, v in sens.regime.value_counts().items()) + ".")
    say("")
    if len(prim):
        say(prim.head(20).round(2).to_markdown(index=False))
        say("")
    ev = sp[sp.source.isin(["in_window_removed", "in_window_censored"])].groupby("Part #").event.sum()
    say(f"Failures per P/N in the primary cohort: ≥ 5: {(ev >= 5).sum()}, ≥ 10: {(ev >= 10).sum()}, ≥ 20: {(ev >= 20).sum()}.")
    say("")

    agg, s = recurrent_tasks(omth, clock)
    st, _ = stoppages(s, agg, r, clock)

    keep = ["Part #", "Serial #", "Aircraft #", "ATA #", "Reason Code", "Reason Category", "Removal Type",
            "Part Type", "Condition", "Attached Part #", "Attached Serial #", "Source Doc #", "Std Cost",
            "Days On A/c", "att", "rem", "event", "tracked"]
    r[keep].to_csv(DERIVED / "removals_clean.csv", index=False)
    sp.to_csv(DERIVED / "spells.csv", index=False)
    prim.to_csv(DERIVED / "weibull_by_pn.csv", index=False)
    sens.to_csv(DERIVED / "weibull_by_pn_sensitivity.csv", index=False)
    clock.round(1).to_csv(DERIVED / "aircraft_fh_daily.csv", index_label="date")
    agg.to_csv(DERIVED / "recurrent_tasks.csv")
    st.to_csv(DERIVED / "stoppages.csv", index=False)
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
