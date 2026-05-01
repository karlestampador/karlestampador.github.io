# STAT 443 — ILI time series and forecasting

*Repository: `stat443_time_series_and_forecasting`*

## 1) Project goal

Forecast weekly influenza-like illness (ILI) using CDC FluView Phase 2 data, and evaluate whether adding external predictors (e.g., lab positivity, age-specific counts) improves forecast accuracy over univariate baselines.

**Primary outcome (from ILINet):**
- `percent_weighted_ili` (recommended), or `percent_unweighted_ili` (if you choose)

**Candidate predictors (examples):**
- lagged age-specific ILI counts (`age_0_4`, `age_5_24`, etc.)
- lagged lab measures from NREVSS (e.g., `percent_positive`, `total_specimens`)
- optional robustness checks: `total_patients` (note: may reflect reporting rather than true incidence)

---

## 2) Repository structure

```
stat443_time_series_and_forecasting/
├── README.md
├── FluViewPhase2Data.zip
├── EstampadorGammaGuentertLardner-Burke-stat443proposal_annotated-2.pdf
├── fluview_raw/
│   ├── ILINet.csv
│   ├── ICL_NREVSS_Clinical_Labs.csv
│   ├── ICL_NREVSS_Public_Health_Labs.csv
│   └── ICL_NREVSS_Combined_prior_to_2015_16.csv
├── fluview_clean/
│   ├── ilinet_clean.csv
│   ├── nrevss_clean.csv
│   ├── plot1_forecast_vs_actual.png
│   └── plot2_abs_errors.png
├── data_cleaning.ipynb
├── data_check_and_plot.ipynb
├── forecast_prototype_karl.ipynb
├── forecast_prototype_karl copy.ipynb
├── forecast_prototype_pascal.ipynb
├── prototype_4cast_michael.ipynb
├── arima_forecast_karl.ipynb
├── arimax_forecast_karl.ipynb
├── exponentialsmoothing_forecast_karl.ipynb
└── forecast_comparison_plots.ipynb
```

Typical flow: place or unpack CDC FluView Phase 2 extracts under `fluview_raw/`, run `data_cleaning.ipynb` to write cleaned tables to `fluview_clean/`, use `data_check_and_plot.ipynb` for EDA, then run the forecast notebooks and `forecast_comparison_plots.ipynb` for models and comparisons. `forecast_prototype_karl copy.ipynb` is a duplicate working copy of the Karl prototype notebook.

Jupyter may create `.ipynb_checkpoints/` while you work; it is not part of the intended tracked layout.

---

## 3) Setup

### 3.1 Install packages
Run once:
```r
install.packages(c(
  "tidyverse","readr","janitor","lubridate","ISOweek",
  "forecast","fable","fabletools","tsibble","feasts",
  "slider","here", "skimr", "naniar", "tsibble", "feasts"
))
