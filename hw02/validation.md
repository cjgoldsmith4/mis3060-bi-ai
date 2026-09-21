# HW2 Validation Record: Wildcat Capital `fact_transactions.csv`

**Script:** `hw02/hw02_eda.py`
**Output checked:** terminal output and `hw02/hw02_profile.txt` from the run on 2026-09-21

---

## 2A: Known-Answer Benchmarks

| Check | Expected | Your Script Produced | Match? | Notes |
|---|---|---|---|---|
| Dataset shape | (298772, 9) | (298772, 9) | Yes | Section 2. Section 14 printed "OK" and no warning. |
| Null count: `security_id` | 101,597 | 101,597 | Yes | Section 4. `shares` and `price` also show 101,597 nulls, so the three columns go null together. |
| Null count: `amount` | 0 | 0 | Yes | Section 4. |
| Unique `txn_type` values | 6 | 6 | Yes | Section 6 lists six types: Buy, Sell, Dividend, Deposit, Advisory Fee, Withdrawal. |
| Count of `Buy` transactions | 83,556 | 83,556 | Yes | Section 6 (27.97% of rows) and Section 11. |
| `txn_date` data type | object | object | Yes | Section 3. The script left the column as text; the date range in Section 8 used a temporary converted copy. |
| Earliest `txn_date` | 2020-01-01 | 2020-01-01 | Yes | Section 8. |
| Latest `txn_date` | 2024-12-30 | 2024-12-30 | Yes | Section 8. The file ends on Dec 30, not Dec 31. |
| Duplicate `txn_id` count | 0 | 0 | Yes | Section 9. |
| Mean `amount` | $54,075.17 | $54,075.17 | Yes | Section 10. |
| Median `amount` | $41,220.48 | $41,220.49 | Yes, within rounding | Section 10. See the investigation below. |
| Skewness of `amount` | 1.15 | 1.15 | Yes | Section 10. Positive skew, and the mean sits above the median, which agrees with the histogram. |
| Correlation `shares`–`amount` | 0.65 | 0.65 | Yes | Section 12. |
| Correlation `price`–`amount` | 0.64 | 0.64 | Yes | Section 12. |
| Correlation `shares`–`price` | 0.00 | 0.00 | Yes | Section 12. Shares and price are independent of each other. |
| Negative `shares` count (Buy only) | 836 | 836 | Yes | Section 13. All 836 negatives fall in `Buy`. Sell and Dividend have a minimum of 1.00, and Deposit, Withdrawal, and Advisory Fee have no share values. The minimum for Buy is -499.63. |
| Profile file created | Yes | Yes | Yes | `hw02/hw02_profile.txt` (about 5.6 KB) exists. |
| Chart files created (3) | Yes | Yes | Yes | `hist_amount.png`, `box_amount_by_type.png`, and `scatter_shares_amount.png` exist in `hw02/charts/`. |

Other values from the run also match the assignment's known grouping benchmark: Dividend $64,077.30 / $48,805.60, Buy $63,738.49 / $47,893.58, Sell $63,635.55 / $48,080.16, Deposit $50,588.07 / $50,760.33, Withdrawal $49,997.34 / $49,843.42, and Advisory Fee $7,375.17 / $859.12 (mean / median), with the same counts and the same highest-to-lowest order.

### Discrepancy investigation: median `amount`

**What differed.** The benchmark says $41,220.48. The script printed $41,220.49, a one-cent gap.

**Investigation.** I asked whether the script or the benchmark was wrong, and checked the unrounded value by loading the CSV in a separate Python call and printing `df["amount"].median()` without any formatting. The result was `41220.485`. The median falls exactly halfway between two cents, so the printed value depends on how a tool rounds a half-cent. The script rounded up to $41,220.49. The benchmark rounded down to $41,220.48, most likely because it was calculated with a different tool or rounding rule. Neither figure is a data or code error.

**Conclusion.** Match, treated as a rounding difference. The underlying median is $41,220.485. All other 17 rows match exactly.

*Investigation done in the Claude Cowork session that generated the script. Paste or link that conversation here if your instructor wants the transcript.*

---

## 2B: Explain the Code and Output

*Prompts run in a new Claude Cowork session, separate from the session that generated `hw02_eda.py`.*

**1. Did Claude's predicted outputs (from Prompt 1) match what you actually saw in the terminal? List any discrepancies.**

Every value in Claude's walkthrough matches the terminal output exactly, with no discrepancies. This is because Claude built its walkthrough from the profile file and chart images already sitting in `hw02` from the earlier run, not from the code alone. That makes the comparison less useful as a blind prediction test than the assignment intends, since Claude effectively had the answer key open while describing the script. The values line up regardless: shape (298772, 9), the 101,597 nulls in `security_id`/`shares`/`price`, the six `txn_type` counts, mean amount $54,075.17, skewness 1.15, and the three correlations all match line for line.

**2. What did Claude flag as potentially unexpected or worth investigating (from Prompt 2)?**

Claude flagged four points worth investigating. The Advisory Fee mean of $7,375.17 runs 8.6 times its median of $859.12, while every other transaction type sits between 1.0 and 1.3 times, which points to a small number of unusually large fees pulling the category average up. The 836 negative `shares` values sit entirely inside `Buy` transactions, with `Sell` and `Dividend` both showing a minimum of 1.00, which doesn't have an obvious business reading since a purchase reducing a share count is not standard. The 0.65 correlation between `shares` and `amount` is moderate rather than close to 1.0, which is worth a spot check if `amount` is assumed to equal `shares` times `price` on trade rows. The `txn_date` and `txn_type` columns print as `str` rather than `object`, which Claude attributed to a newer pandas version and called cosmetic, not a data problem. Claude also flagged two purely cosmetic items: the date range ending December 30 instead of December 31, and a `MatplotlibDeprecationWarning` on the box plot's `vert=False` argument that will need to become `orientation="horizontal"` in a future Matplotlib release.

**3. Did Claude mention the 101,597 null values in `security_id`? What explanation did it give?**

Yes. Claude explained the nulls as structural rather than a data quality problem. This is because the 101,597 figure equals the row counts for Deposit (35,981), Advisory Fee (35,766), and Withdrawal (29,850) added together, and those three transaction types are cash movements with no security attached, so a null `security_id`, `shares`, and `price` on those rows is what the business logic of the file would predict rather than a loading error.

**4. Did Claude flag the `txn_date` column as a concern? Why would that matter for a time-series analysis?**

Claude flagged `txn_date` only for its dtype label, not for its type. It noted the column prints as `str` instead of `object` in this pandas version, called the difference cosmetic, and did not connect it to time-series risk. That's a gap worth filling in myself: as long as `txn_date` stays text, pandas sorts and compares the values character by character rather than by calendar date, so a string sort works only because the format is already `YYYY-MM-DD` and happens to sort correctly by coincidence, not by design. Date arithmetic — days between transactions, resampling to monthly totals, rolling windows — isn't available on a text column at all and would need `pd.to_datetime()` first, which is exactly the conversion the script deliberately avoided in order to leave the loaded dtype matching the benchmark.

**5. Open your three chart files. Does what you see in each image match Claude's explanation of that section of the output? Note any differences.**

The histogram matches: the bulk of transactions cluster under $50,000, the distribution has a long right tail out past $200,000, and the red mean line sits to the right of the green median line, consistent with the 1.15 skewness Claude described. The box plot matches too: Advisory Fee shows a small box near zero with a long tail of individual outlier points, exactly the pattern Claude used to explain the 8.6x mean-to-median ratio, while Deposit and Withdrawal show tight, symmetric boxes with no outliers. One difference worth noting in the scatter plot: Claude's explanation treats all three trade types (Dividend, Buy, Sell) as visible in the legend, but in the actual image the Dividend points (light blue) are almost entirely hidden underneath the Sell (green) and Buy (orange) points, since Dividend is plotted first and the later series draw on top of it. The chart still shows the two-sided fan shape — negative-and-positive on the Buy/left side, positive-only on the Sell/right side — that the explanation describes, but a reader would not know Dividend transactions are present at all from the image alone.

**6. Follow-up question and Claude's answer.**

> **Question:** The Advisory Fee mean of $7,375.17 runs 8.6 times its median of $859.12, and you flagged that as a handful of large fees skewing the category. What's a quick way to check that in pandas, and how much of total Advisory Fee dollar volume do the outliers account for?

> **Answer:** Use the standard IQR fence on the Advisory Fee subset: take Q1 and Q3 of `amount` for rows where `txn_type == "Advisory Fee"`, compute `IQR = Q3 - Q1`, and flag anything above `Q3 + 1.5 * IQR` as an outlier. On this file, Q1 is $428.09 and Q3 is $4,653.68, which puts the upper fence at $10,992.07. That flags 4,117 of the 35,766 Advisory Fee transactions, 11.5% of the category by count, but those 4,117 rows account for $203.4 million of the $263.8 million in total Advisory Fee dollar volume, 77.1% of the category's total. The five largest individual fees run from $141,275 to $142,855, roughly 150 to 165 times the category median. A count this large above the fence, carrying this much of the dollar total, argues against a handful of stray entry errors and toward a real second population inside the category, such as an annual or performance-based fee that only some clients or some periods incur, layered on top of the smaller recurring fees the median reflects.

---

## 2C: Business Check and Cross-Validation

### Business-reasonableness questions

**1. `security_id`, `shares`, and `price` are all null in exactly 101,597 rows. Which three transaction types would you expect to have no security, and why? Do the counts add up to 101,597?**

Deposit, Advisory Fee, and Withdrawal are the three transaction types that should have no security. This is because each one is a cash movement rather than a trade: a deposit adds cash to the account, a withdrawal removes it, and an advisory fee is a charge against the account balance, and none of the three involves buying or selling a specific holding, so there is nothing to put in `security_id`, `shares`, or `price`. The counts confirm it directly: Deposit has 35,981 rows, Advisory Fee has 35,766 rows, and Withdrawal has 29,850 rows, and 35,981 + 35,766 + 29,850 = 101,597, matching the null count exactly. Because the three non-trade types account for the full null count with nothing left over, the missingness is a byproduct of the transaction type, not a gap in the data.

**2. There are 83,556 Buy transactions and 59,755 Sell transactions. What does it mean for a wealth management firm to have significantly more Buys than Sells over a five-year period?**

More Buys than Sells over a five-year period means the firm's client base is net accumulating assets rather than distributing them. This is consistent with a growing book of business: as existing clients keep contributing and new clients (2,700 of them, per item 7) get onboarded and their cash gets invested, each new dollar into the market shows up as a Buy, while Sells only happen when a client rebalances, raises cash, or exits a position. It also fits 2020 to 2024 as a mostly rising five-year market window, where advisors are more likely to be putting new and reinvested money to work than trimming winners. A Buy-heavy book is not itself a red flag; it is what you would expect from a firm in growth mode with a client base still in the accumulation phase of their investing life rather than the drawdown phase.

**3. The `txn_date` column is stored as a string rather than a date. If Claude Cowork generated code to compute the average number of days between transactions, what would go wrong if the dates remained as strings?**

Subtraction between two `txn_date` strings would fail outright rather than produce a wrong number. This is because Python and pandas do not define a minus operation for two strings, so a line like `df["txn_date"].diff()` on the unconverted column raises a `TypeError` before any average gets computed, forcing the error to surface immediately rather than passing silently into a report. The dataset happens to sort correctly as plain text right now, since the format is zero-padded `YYYY-MM-DD` and alphabetical order matches chronological order for that format, but that is a coincidence of formatting, not a property of text generally, and it would break the moment a date appeared in a different format like `1/5/2024` or `Jan 5, 2024`. Any calculation that depends on real date math, not just sort order, needs `pd.to_datetime()` first, which converts the column to a type that supports subtraction and returns actual day counts instead of an error.

**4. Wildcat Capital has 2,700 clients served by 25 advisors. Is that ratio, roughly 108 clients per advisor, plausible for a registered investment advisory firm?**

Yes, 108 clients per advisor is plausible and sits close to the industry's own recommended range. SmartAsset's advisor-resources research puts the industry-wide average at approximately 173 clients per registered advisor, calculated from 73.7 million total clients across 426,364 registered Investment Adviser Representatives, while the median firm serves 73 clients and the article's suggested comfortable range for an individual advisor runs from 50 to 150 clients depending on firm size and niche. Wildcat's 108-per-advisor figure falls inside that 50-to-150 range and below the industry average of 173, which points to a firm staffed for high-touch service rather than one stretched thin across too many relationships.

**5. 836 `Buy` transactions have negative `shares` values, as low as −499.63. What are two plausible business explanations, and what would you do next to determine which is more likely?**

Two plausible explanations are a data-entry sign error and a legitimate correction or reversal entry. A sign error would mean someone, or an automated feed, flipped the sign on the share count during entry, most likely on the same 836 rows regardless of client, advisor, or date, with no other pattern behind it. A correction or reversal would mean each negative row is deliberately offsetting an earlier Buy that was entered incorrectly, in which case each negative row should pair up with a matching positive Buy of the same size for the same client and security.

I checked the second explanation directly against the data and did not find that pairing: none of the 836 negative rows have an exact opposite-sign match in `shares` for the same `client_id` and `security_id` anywhere else in the file, on any date. The negative rows are also spread close to evenly across advisors, from 37 to 47 rows per advisor across all 25, and close to evenly across the five years, running from 118 in 2020 up to 196 in 2024, in line with the dataset's overall growth in Buy volume rather than clustered in one advisor's book or one time period. Combined with the fact that negative rows are only 1.00% of all Buy transactions, this pattern looks more like a scattered entry or import error across the whole book than a deliberate reversal convention, since a reversal process would be expected to leave a visible offsetting trade and would more plausibly cluster around specific advisors or a specific system change rather than distributing itself proportionally across every advisor and every year. To settle it, the next step is to ask whoever built or sourced the file whether negative `shares` is a documented convention anywhere in the system, and if not, to pull a handful of the 836 rows and check them against the source order records or custodian statements to see whether the true transaction was actually a Sell, a smaller Buy, or something else entirely.

*Sources: [Average Number of Clients Per Financial Advisor](https://smartasset.com/advisor-resources/average-number-of-clients-per-financial-advisor)*

### Cross-validation

**Prompt A:** *"Write Python to count rows in fact_transactions.csv where txn_type equals exactly 'Buy'."*
**Prompt B:** *"Write Python to count the total rows in fact_transactions.csv, then subtract the count of rows where txn_type is Sell, Deposit, Withdrawal, Dividend, or Advisory Fee."*

**6. What did each script return?**

Prompt A, the direct filter, returned 83,556 for rows where `txn_type` equals exactly `Buy`. Prompt B, the subtraction approach, returned the same 83,556: it counted 298,772 total rows, counted 215,216 rows across the five non-Buy types (Sell, Deposit, Withdrawal, Dividend, Advisory Fee), and subtracted the two (298,772 − 215,216 = 83,556).

**7. Do the results agree? If not, which one is wrong and why?**

The results agree exactly at 83,556, so neither script needs to be treated as wrong. This is because the two approaches ask the question from opposite directions: Prompt A counts the rows that belong to `Buy`, and Prompt B counts everything that does not belong to any of the other five types, and since `txn_type` only ever holds one of six values (confirmed back in item 6 of the EDA script), those two counts have to land on the same number if the data and the code are both correct. Getting 83,556 from both methods, matching the assignment's known-answer benchmark, is strong evidence the Buy count is right and that there is no seventh, uncategorized `txn_type` value hiding in the file that either script mishandled.

**8. Why is it useful to verify a count using subtraction rather than direct filtering?**

Subtraction is useful because it reaches the same number through a completely different mechanism, so the two methods are unlikely to share the same bug. This is because a direct filter and a subtraction only fail in different ways: a typo in the filter string, like `"buy"` instead of `"Buy"`, would silently undercount Prompt A without touching Prompt B at all, while a missing entry in Prompt B's exclusion list, such as forgetting `Advisory Fee`, would inflate its result without touching Prompt A. Running both and getting the same answer rules out that category of error in a way that running the same filter twice never could, since two independent paths landing on 83,556 is a stronger check than one path checked twice.
