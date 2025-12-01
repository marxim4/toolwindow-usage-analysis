# Tool Window Usage Analysis

### JetBrains “Analytics for Data Products – IDEs” Internship Task

**Author:** Marko Perunović

---

## 1. Objective

This analysis investigates whether a particular IDE tool window stays open longer when:

* **Manually opened** (user action), or
* **Automatically opened** (IDE-triggered event such as test failures or starting debug mode).

The dataset contains timestamped open/close events for a single tool window, grouped by anonymized users.

---

## 2. Dataset Description

Each event includes:

* `user_id` — anonymized user identifier
* `timestamp` — epoch milliseconds
* `event_id` — `"open"` or `"close"`
* `open_type` — `"manual"` or `"auto"` (for open events only)

The dataset intentionally includes real-world imperfections:

* **Orphan closes:** close without prior open
* **Multiple opens:** back-to-back open events
* **Missing closes:** open events without a closing event before the dataset ends
* **Mixed ordering:** events occurring at identical timestamps

The goal is to robustly reconstruct true open/close *intervals* from this noisy stream.

---

## 3. Methodology

### 3.1 Event Normalization

Before interval reconstruction, all events are cleaned and standardized:

* Convert timestamps to integer epoch milliseconds
* Normalize event types (`"open"` → `"opened"`, `"close"` → `"closed"`)
* Drop invalid open types
* Ensure ordering: if two events share the same timestamp, **closed events are processed first**
* Sort events per user → by timestamp → by event type

---

### 3.2 Interval Reconstruction Logic

For each user, events are processed in chronological order:

#### Rules

* **Opened event**

  * If no interval open → start new interval
  * If interval already open → close previous implicitly, start new interval

* **Closed event**

  * If interval open → close it
  * If no interval open → ignore (orphan close)

* **End of dataset**

  * Any still-open interval becomes **right-censored**

Each interval contains:

| Field          | Description                                          |
| -------------- | ---------------------------------------------------- |
| user_id        | Interval owner                                       |
| open_ts        | Timestamp of window opening                          |
| close_ts       | Timestamp of window closing (may be NaN if censored) |
| open_type      | manual / auto                                        |
| censored       | Whether close event was missing                      |
| implicit_close | Closed by a new open event                           |
| duration_ms    | close_ts - open_ts (if not censored)                 |

---

## 4. Descriptive Statistics

Only **completed** (non-censored) intervals with valid `open_type` are used for duration statistics.

### Summary (from the provided dataset)

| Metric          | Manual      | Auto         |
| --------------- | ----------- | ------------ |
| Count (n)       | 651         | 1180         |
| Median duration | ~14 seconds | ~285 seconds |
| Mean duration   | ~4.6M ms    | ~17.5M ms    |
| Variability     | Lower       | Much higher  |

**Auto-opened tool windows stay open dramatically longer**.

---

## 5. Statistical Significance Test

Because interval durations are extremely right-skewed, durations were **log-transformed** before testing.

### Welch's t-test on log durations

| Statistic   | Value                             |
| ----------- | --------------------------------- |
| t-statistic | ≈ 19.33                           |
| p-value     | ≈ 1.2 × 10⁻⁷³                     |
| Effect size | mean(auto) ≈ **16×** mean(manual) |

### Interpretation

The difference in durations between manual and auto opens is:

* **Huge in magnitude**
* **Extremely statistically significant**
* **Highly robust across users**

Auto windows remain open approximately an *order of magnitude longer*.

---

## 6. Implicit-Close Transition Analysis

Some intervals end not by the user closing the window, but because a new open event automatically closed the previous interval.

A transition matrix shows what type of open followed an implicit close:

| Previous → Next | Auto | Manual |
| --------------- | ---- | ------ |
| **Auto**        | 170  | 10     |
| **Manual**      | 25   | 4      |

### Interpretation

* Auto→Auto transitions dominate → automated workflows cluster
* Manual→Auto transitions are more common than Manual→Manual
* IDE-driven events frequently "take over" user-driven window usage

---

## 7. Visualizations

The following figures were generated from the dataset:

### • Count of Completed Intervals

`plot_counts_by_open_type.png`

### • Duration Histogram (log-scale)

`plot_hist_log_seconds.png`

### • ECDF Comparison (log-scale)

`plot_ecdf_log_seconds.png`

### • Log-scale Boxplot

`plot_boxplot_log_seconds.png`

These visualizations clearly show that auto-opened intervals are longer and more variable.

---

## 8. Conclusions

* **Auto-opened tool windows remain open far longer** than manually opened ones
* The difference is **~16× on average** and **statistically decisive**
* The analysis pipeline is robust to messy telemetry (implicit closes, orphan closes, censored data)
* The event reconstruction logic can be reused for other IDE windows or UI components
* The results match expectations: IDE-triggered windows usually appear during extended workflows (debugging, test runs)

---

## 9. Potential Extensions

If expanded into production research, next steps would include:

* **Survival analysis** (Kaplan–Meier curves, Cox models) to incorporate censored intervals
* **Modeling durations** via regression with user-level random effects
* **Cross-tool-window comparisons** across different JetBrains IDEs
* **A/B tests** on opening/closing behavior, visibility defaults, and UI positioning

---

## 10. Repository Contents

* `main.py` — full analysis code
* `README.md` — project overview
* `REPORT.md` — this detailed analysis
* `plot_*.png` — generated visualizations
* `requirements.txt` — dependencies

---

## 11. Notes on Feedback

This project includes enhancements made after receiving positive, constructive feedback from JetBrains, specifically:

* Adding a formal statistical test to strengthen the conclusions, as a refinement suggested during feedback
* Improving documentation clarity
* Strengthening the analysis narrative

 