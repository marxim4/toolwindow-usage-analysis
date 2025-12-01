import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

DATA_PATH = Path("toolwindow_data.csv")


def load_events(path: Path) -> pd.DataFrame:
    """
    Load the raw toolwindow log and normalize it.

    Expected columns:
      - user_id
      - timestamp (epoch ms)
      - event or event_id: open/close or opened/closed
      - open_type: manual/auto for open events
    """
    df = pd.read_csv(path)

    df["user_id"] = df["user_id"].astype(str)
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()
    df["timestamp"] = df["timestamp"].astype("int64")

    if "event_id" in df.columns and "event" not in df.columns:
        df = df.rename(columns={"event_id": "event"})

    df["event"] = df["event"].astype(str).str.lower()
    df["event"] = df["event"].replace({"open": "opened", "close": "closed"})

    valid = df["event"].isin(["opened", "closed"])
    if (~valid).any():
        print(f"[warn] dropping {(~valid).sum()} rows with unknown event")
        df = df[valid].copy()

    if "open_type" not in df.columns:
        df["open_type"] = ""

    is_opened = df["event"] == "opened"
    df.loc[is_opened, "open_type"] = df.loc[is_opened, "open_type"].astype(str).str.lower()
    good_type = df.loc[is_opened, "open_type"].isin(["manual", "auto"])

    if (~good_type).any():
        dropped = (~good_type).sum()
        print(f"[warn] dropped {dropped} 'opened' rows with missing/invalid open_type")
        df = df.drop(df.loc[is_opened & ~good_type].index)

    # open_type doesn't matter on closes
    df.loc[df["event"] == "closed", "open_type"] = ""

    # at the same timestamp, close before open
    order = {"closed": 0, "opened": 1}
    df["_order"] = df["event"].map(order)
    df = df.sort_values(["user_id", "timestamp", "_order"]).drop(columns="_order")

    return df


def reconstruct_intervals(events: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruct open/close intervals per user.

    Rules:
      - multiple 'opened' in a row => implicit close of previous interval
      - 'closed' without a previous open => ignored
      - open without a close before dataset end => censored
    """
    rows = []

    for user, g in events.groupby("user_id", sort=False):
        open_ts = None
        open_type = None

        for _, r in g.iterrows():
            ev = r["event"]
            ts = int(r["timestamp"])
            ot = (r.get("open_type") or "").strip().lower()

            if ev == "opened":
                if open_ts is not None:
                    rows.append(
                        {
                            "user_id": user,
                            "open_ts": open_ts,
                            "close_ts": ts,
                            "open_type": open_type,
                            "censored": False,
                            "implicit_close": True,
                        }
                    )
                open_ts = ts
                open_type = ot

            elif ev == "closed":
                if open_ts is None:
                    continue
                rows.append(
                    {
                        "user_id": user,
                        "open_ts": open_ts,
                        "close_ts": ts,
                        "open_type": open_type,
                        "censored": False,
                        "implicit_close": False,
                    }
                )
                open_ts = None
                open_type = None

        if open_ts is not None:
            rows.append(
                {
                    "user_id": user,
                    "open_ts": open_ts,
                    "close_ts": np.nan,
                    "open_type": open_type,
                    "censored": True,
                    "implicit_close": False,
                }
            )

    ep = pd.DataFrame(rows)
    if ep.empty:
        return ep

    ep["duration_ms"] = np.where(ep["censored"], np.nan, ep["close_ts"] - ep["open_ts"])
    ep = ep[(ep["censored"]) | (ep["duration_ms"] > 0)].copy()

    return ep


def ecdf(x: np.ndarray):
    x = np.sort(x)
    y = np.arange(1, len(x) + 1) / len(x)
    return x, y


def main():
    print(f"Loading: {DATA_PATH.resolve()}")
    events = load_events(DATA_PATH)
    print(f"Events: {len(events):,}")

    intervals = reconstruct_intervals(events)
    print(f"Intervals: {len(intervals):,}")
    print(f"Censored intervals: {intervals['censored'].sum():,}")

    intervals.to_csv("toolwindow_intervals.csv", index=False)
    print("Wrote toolwindow_intervals.csv")

    complete = intervals[~intervals["censored"]].copy()
    complete = complete[complete["open_type"].isin(["manual", "auto"])].copy()

    if complete.empty:
        print("No completed intervals with valid open_type. Exiting.")
        return

    complete["duration_s"] = complete["duration_ms"] / 1000.0

    summary = (
        complete.groupby("open_type")["duration_ms"]
        .agg(
            n="size",
            mean_ms="mean",
            median_ms="median",
            p25_ms=lambda s: s.quantile(0.25),
            p75_ms=lambda s: s.quantile(0.75),
            p90_ms=lambda s: s.quantile(0.90),
            std_ms="std",
        )
        .reset_index()
    )
    print("\nSummary by open_type:\n", summary.to_string(index=False))
    summary.to_csv("summary_by_open_type.csv", index=False)
    print("Wrote summary_by_open_type.csv")

    manual = complete.loc[complete["open_type"] == "manual", "duration_s"].values
    auto = complete.loc[complete["open_type"] == "auto", "duration_s"].values

    if len(manual) > 1 and len(auto) > 1:
        manual_log = np.log(manual)
        auto_log = np.log(auto)

        t_stat, p_val = stats.ttest_ind(auto_log, manual_log, equal_var=False)
        diff_log = auto_log.mean() - manual_log.mean()
        ratio = np.exp(diff_log)

        print("\n=== Welch t-test on log durations ===")
        print(f"t = {t_stat:.3f}, p = {p_val:.3e}")
        print(f"Estimated mean(auto) / mean(manual) ≈ {ratio:.2f}x")
    else:
        print("\nNot enough data for a statistical test.\n")

    intervals_sorted = intervals.sort_values(["user_id", "open_ts"]).copy()
    intervals_sorted["seq"] = intervals_sorted.groupby("user_id").cumcount()

    implicit = intervals_sorted.loc[
        (~intervals_sorted["censored"]) & (intervals_sorted["implicit_close"]),
        ["user_id", "seq", "open_type"],
    ].copy()
    implicit["seq_next"] = implicit["seq"] + 1

    next_map = intervals_sorted[["user_id", "seq", "open_type"]].rename(
        columns={"open_type": "next_open_type"}
    )

    next_pairs = implicit.merge(
        next_map,
        left_on=["user_id", "seq_next"],
        right_on=["user_id", "seq"],
        how="left",
        suffixes=("", "_y"),
    )

    transition_counts = (
        next_pairs.dropna(subset=["next_open_type"])
        .value_counts(["open_type", "next_open_type"])
        .rename("count")
        .reset_index()
        .pivot(index="open_type", columns="next_open_type", values="count")
        .fillna(0)
        .astype(int)
    )

    print("\nImplicit-close transitions:\n", transition_counts)
    transition_counts.to_csv("implicit_transition_counts.csv")
    print("Wrote implicit_transition_counts.csv")

    print("\nGenerating plots...")

    counts = complete["open_type"].value_counts().sort_index()
    plt.figure(figsize=(6, 4))
    plt.bar(counts.index.astype(str), counts.values)
    plt.title("Count of Completed Intervals by Open Type")
    plt.xlabel("open_type")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig("plot_counts_by_open_type.png", dpi=150)
    plt.close()

    complete["duration_s"] = complete["duration_s"].clip(lower=1e-6)
    bins = np.logspace(
        np.log10(complete["duration_s"].min()),
        np.log10(complete["duration_s"].max()),
        50,
    )

    plt.figure(figsize=(8, 5))
    for t in ["manual", "auto"]:
        data = complete.loc[complete["open_type"] == t, "duration_s"].values
        if len(data) == 0:
            continue
        plt.hist(data, bins=bins, alpha=0.5, label=t)
    plt.xscale("log")
    plt.title("Duration Histogram (seconds, log scale)")
    plt.xlabel("duration (s, log)")
    plt.ylabel("count")
    plt.legend(title="open_type")
    plt.tight_layout()
    plt.savefig("plot_hist_log_seconds.png", dpi=150)
    plt.close()

    plt.figure(figsize=(8, 5))
    for t in ["manual", "auto"]:
        data = complete.loc[complete["open_type"] == t, "duration_s"].values
        if len(data) == 0:
            continue
        xs, ys = ecdf(data)
        plt.plot(xs, ys, drawstyle="steps-post", label=t)
    plt.xscale("log")
    plt.title("ECDF of Interval Duration (seconds, log x)")
    plt.xlabel("duration (s, log)")
    plt.ylabel("F(x)")
    plt.legend(title="open_type", loc="lower right")
    plt.tight_layout()
    plt.savefig("plot_ecdf_log_seconds.png", dpi=150)
    plt.close()

    groups = ["manual", "auto"]
    data = [complete.loc[complete["open_type"] == t, "duration_s"].values for t in groups]
    plt.figure(figsize=(7, 5))
    plt.boxplot(data, labels=groups, showfliers=False)
    plt.yscale("log")
    plt.title("Boxplot of Duration (seconds, log scale)")
    plt.xlabel("open_type")
    plt.ylabel("duration (s, log)")
    plt.tight_layout()
    plt.savefig("plot_boxplot_log_seconds.png", dpi=150)
    plt.close()

    print("\nSaved figures:")
    print(" - plot_counts_by_open_type.png")
    print(" - plot_hist_log_seconds.png")
    print(" - plot_ecdf_log_seconds.png")
    print(" - plot_boxplot_log_seconds.png")
    print("\nDone.")


if __name__ == "__main__":
    main()
