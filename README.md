# Tool Window Usage Analysis (JetBrains Internship Task)

This project analyzes tool window usage patterns in JetBrains IDEs, focusing on
whether a tool window stays open longer when it is opened **manually** (user action)
or **automatically** (IDE-triggered event such as debugging or test failure).

The project originated as a **technical take-home assignment** for the  
**JetBrains “Analytics for Data Products – IDEs” internship**.

This repository extends my original submission with 
additional statistical testing and improved documentation, 
based on helpful feedback from JetBrains.

---

## Background: JetBrains Task Summary

JetBrains asked candidates to analyze real IDE telemetry and answer:

> **Do manually opened tool windows behave differently from automatically opened ones?**

The dataset included events like:

- `user_id`
- `timestamp` (epoch ms)
- `event_id`: `"open"` or `"close"`
- `open_type`: `"manual"` or `"auto"`

The analysis required:

- Cleaning messy real-world logs  
- Reconstructing tool window open/close intervals  
- Computing durations  
- Comparing manual vs auto opens  
- Testing whether differences are statistically significant  
- Producing summary statistics and visualizations  
- Writing a short analysis summary  

<details>
<summary><strong>Click to view the full task description</strong></summary>

Description  
Work with real IDE usage data (from PyCharm and other JetBrains IDEs) to identify what actually helps developers and what gets in their way. You'll define clear metrics, run analyses, and validate changes that make developers faster and the UI less distracting.

**Example projects:**

Quantify the impact of Python type checkers  
Python doesn’t have strict static typing. In PyCharm we show type-related problems before you run code. Do these checks actually help?

Understand whether pre-run type checks help reduce common runtime errors and speed up the feedback loop, so we can decide how much to invest in them.

**Outcomes to examine:**

- Runtime TypeError/AttributeError per runs/tests  
- Time and attempts to reach "all tests green"  
- Navigation and code completion efficiency (e.g., jumps to definition per hour, completion acceptance rate)

**What you’ll do:**

- Define metrics for how much typing/checking is used in a project or session  
- Define analysis sessions (e.g., from first failing test to all tests passing, or one debug/run cycle)  
- Compare results across projects and before/after enabling type checks

---

### Measure UI element clutter and usefulness

Goal: Our IDEs have many buttons, panels, and tool windows. Some are very helpful, others take space but add little. We want the UI to feel lighter without hurting power users.

Identify low-value, high-space elements and propose better defaults, placement, or removal.

**Outcomes to examine:**

- "Good” vs “bad” clicks (rage, dead, bounce)
- Passive value (panels rarely clicked but useful to glance at)
- Placement (first screenful visibility, top-of-menu spots)
- Friction (open–close–open loops, repeated searches for the same command, long time-to-command)

**What you’ll do:**

- Create usefulness/cost/friction scores  
- Rank candidates for hide/reposition/remove  
- Estimate “position lift”  
- Optionally validate with A/B tests

**Requirements:**  
Python, SQL, Statistics

---

### Task #1 — Analyze Toolwindow Usage Data

Each row contains:

- user_id  
- timestamp  
- event_id (`open` / `close`)  
- open_type (`manual` / `auto` for opens only)

Data is messy: orphan closes, repeated opens, missing closes, etc.

**Objective**

- Match open/close event pairs  
- Reconstruct complete toolwindow “episodes”  
- Calculate duration  
- Compare manual vs auto durations  
- Determine statistical significance

</details>

---

## What This Repository Contains

- **A clean Python analysis pipeline** (`main.py`)
- **Interval reconstruction logic**, handling:
  - Orphan closes  
  - Implicit closes (multiple opens in a row)  
  - Right-censored intervals  
- **Duration statistics per open_type**
- **Welch t-test** on log durations (statistical significance)
- **Transition analysis** (what users open after an implicit close)
- **Visualizations** (saved as PNGs)
- **Optional synthetic example CSV**

The real JetBrains dataset is **not included**, but the code and example data
allow the full pipeline to be run.

---

## Improvements Made After Feedback

JetBrains provided helpful and constructive feedback:

> *“Your analysis showed solid data handling and clear reasoning.  
> For future analytics work, consider including statistical tests to formally assess differences.”*

This improved version adds:

-  Welch’s t-test on log-transformed durations  
-  Effect-size estimation (auto/manual ratio)  
-  Clearer interval reconstruction docstrings  
-  Polished visualizations  
-  Expanded README with task summary and findings  

---

## Key Results (Based on the Provided Dataset)

### Completed Intervals

- **Auto opens:** 1,180  
- **Manual opens:** 651  

### Duration Comparison

| Metric          | Manual      | Auto         |
|-----------------|-------------|--------------|
| Median duration | ~14 seconds | ~285 seconds |
| Mean duration   | ~4.6M ms    | ~17.5M ms    |
| Variability     | Lower       | Much higher  |

### Statistical Significance

- Welch t-test on log durations:  
  **t ≈ 19.33, p ≈ 1.2 × 10⁻⁷³**  
- Estimated mean ratio:  
  **Auto durations ≈ 16× longer than manual**

**Conclusion:**  
Auto-opened tool windows remain open **dramatically longer**, and the difference is **highly statistically significant**.

---

## Visualizations

These plots were generated by the analysis:

### 1. Count of Completed Intervals
![counts](plot_counts_by_open_type.png)

### 2. ECDF of Durations
![ecdf](plot_ecdf_log_seconds.png)

### 3. Histogram (log-scale)
![hist](plot_hist_log_seconds.png)

### 4. Log-scale Boxplot
![boxplot](plot_boxplot_log_seconds.png)

---

## Running the Analysis

### Requirements

- Python 3.9+
- Install dependencies:

```bash
pip install -r requirements.txt
