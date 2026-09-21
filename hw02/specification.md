# HW2 Specification: EDA Script for the Wildcat Capital Transaction Portfolio

**Course:** MIS3060 Business Intelligence with AI
**Author:** Charlie
**Dataset:** `fact_transactions.csv` (Wildcat Capital client transactions, January 2020 through December 2024)

## What I need

Write one Python script that performs an exploratory data analysis (EDA) of the Wildcat Capital transaction file. Save it as `hw02/hw02_eda.py`. The script must run from the repository root with the command `python hw02/hw02_eda.py`, use pandas, numpy, matplotlib, and scipy where needed, and finish every task below in a single execution. It should not need any input from me while it runs.

All file paths in the script are relative to the repository root. The script should create the `hw02/charts/` folder if it does not exist. Charts must save to files and never open a window on screen.

The file has nine columns: `txn_id`, `client_id`, `advisor_id`, `security_id`, `txn_date`, `txn_type`, `shares`, `price`, and `amount`. Use those exact column names.

Each section of the output should carry a short numbered heading that matches the item below, so I can find each result in the terminal and in the profile file. Wrap the work in clearly named functions or clearly separated blocks, and add brief comments that explain each step in plain language.

## Steps the script must perform

1. **Load the data.** Read `data/raw/fact_transactions.csv` into a pandas DataFrame. Do not convert any column types while loading. I want to see the types pandas assigns on its own, and the `txn_date` column must stay as text (an object column).

2. **Shape.** Print the number of rows and the number of columns.

3. **Columns and data types.** Print every column name next to its data type.

4. **Missing values.** Print the count of missing values for every column.

5. **Descriptive statistics.** Print the count, mean, standard deviation, minimum, 25th percentile, median, 75th percentile, and maximum for every numeric column.

6. **Transaction type counts.** Print the count and the percentage of rows for each value in `txn_type`, sorted from the most frequent to the least frequent.

7. **Unique counts.** Print the number of unique clients, unique advisors, and unique securities in the file. Use the `client_id`, `advisor_id`, and `security_id` columns. Do not count missing values as a security.

8. **Date range.** Print the earliest and latest `txn_date`. Because the dates are stored as text, work on a temporary date-converted copy of the column for this step so the original DataFrame column keeps its text type.

9. **Duplicates.** Check for duplicate values in `txn_id` and print the number of duplicates.

10. **Amount statistics.** Print the mean, median, and skewness of the `amount` column, and state in words whether the distribution is skewed right, skewed left, or roughly symmetric.

11. **Amount by transaction type.** Group the data by `txn_type`. For each type, print the row count, the mean `amount`, and the median `amount`, with the amounts rounded to two decimal places. Sort the table by mean `amount` from highest to lowest.

12. **Correlations.** Compute the correlation matrix for `shares`, `price`, and `amount`, round it to two decimal places, and print it. Then list the three strongest pairwise correlations by absolute value, leaving out each variable's correlation with itself and listing each pair only once.

13. **Shares check.** For the `shares` column, print the minimum, the maximum, and the number of negative values, broken out by `txn_type`. Include every transaction type in the table, even those with no share values.

14. **Shape warning.** Compare the shape to the expected 298,772 rows by 9 columns. If it differs, print a clear warning that shows the expected shape and the actual shape. If it matches, print a short confirmation.

15. **Charts.** Create and save three charts, each with a clear title, labeled axes, and readable text:
    - A histogram of `amount`, saved as `hw02/charts/hist_amount.png`. Draw one vertical line at the mean and a different vertical line at the median. Use different colors, and add a legend that names each line and shows its dollar value.
    - A horizontal box plot of `amount` by `txn_type`, saved as `hw02/charts/box_amount_by_type.png`. Show one box per transaction type, with the transaction types on the vertical axis and `amount` on the horizontal axis.
    - A scatter plot of `shares` on the horizontal axis against `amount` on the vertical axis, saved as `hw02/charts/scatter_shares_amount.png`. Color the points by `txn_type` and include a legend. The file has nearly 300,000 rows, so use small, partly transparent markers to keep the plot readable. Skip rows where `shares` is missing.

    Print a line for each chart confirming that it was saved and where.

16. **Profile file.** Save a plain-text summary of the results from items 2 through 13 to `hw02/hw02_profile.txt`. The file should contain the same information the terminal shows for those items, under the same numbered headings, so someone can read it without running the script. Print a confirmation line when the file is saved.

17. **Header comment block.** Start the script with a comment block that identifies the script name, the dataset, the author (Charlie), the course (MIS3060), and the date the script was generated.

## Rules for the whole script

- This is one script that runs all 17 items in one execution. Do not split the work into several files.
- The script must run without errors on a standard Windows machine with Python and the libraries above installed.
- The terminal output and the profile file should use plain text with clear section headings and aligned tables. Use readable number formatting, such as thousands separators for counts and two decimal places for dollar amounts.
- Do not change, drop, or fill in any data. This script only inspects the data.
- After the script is done, print a short closing line that says the run finished and lists the output files it created.
