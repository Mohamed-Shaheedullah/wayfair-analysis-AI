## Instructions
We will perform data analysis on a dataset downloaded from 
https://www.datacareerschool.com/datalabs/ecommerce-sales-analysis
This is Wayfair e-commerce data.
This will be done in python and tracked in git.  
Do not do anything to the repo without asking human user first, we will go through Codex plan (last section) point by point .

## Data Dictionary
### orders.csv

One row per order placed between January 2024 and December 2025.

9,245 rows · 7 columns · 516 KB

| Column         | Type     | Description                                                |
| -------------- | -------- | ---------------------------------------------------------- |
| order_id       | integer  | Unique ID of the order.                                    |
| customer_id    | integer  | The customer who placed the order.                         |
| order_date     | datetime | When the order was placed (UTC).                           |
| status         | text     | Final state of the order: completed, canceled or returned. |
| payment_method | text     | How the customer paid.                                     |
| discount_code  | text     | Promo code used on the order, if any.                      |
| shipping_fee   | decimal  | Shipping charged to the customer, in USD.                  |


### order_items.csv

One row per product line in an order.

15,608 rows · 5 columns · 347 KB

| Column          | Type    | Description                                                           |
| --------------- | ------- | --------------------------------------------------------------------- |
| order_id        | integer | The order this line belongs to.                                       |
| product_id      | integer | The product bought.                                                   |
| quantity        | integer | Number of units bought.                                               |
| unit_price      | decimal | Price of one unit at the time of the order, in USD, before discounts. |
| discount_amount | decimal | Total discount taken off this line, in USD.                           |


### products.csv

The store's product catalog.

90 rows · 5 columns · 4 KB

| Column       | Type    | Description                            |
| ------------ | ------- | -------------------------------------- |
| product_id   | integer | Unique ID of the product.              |
| product_name | text    | Name shown on the website.             |
| category     | text    | Product category.                      |
| list_price   | decimal | Current catalog price, in USD.         |
| unit_cost    | decimal | What one unit costs the store, in USD. |
## Brief
### Your task

Clean the store's order data, then build a short sales review that shows how revenue changed over the two years, what drove it, and where the business should focus next year.

## Instructions

1. Load the three files and check each one for problems before you analyze anything, such as repeated records, inconsistent labels and missing values. Fix what you find and note every decision you made.
2. Decide which orders count as revenue and how to calculate revenue for an order. Write your definition down so anyone reading your work can follow it.
3. Show how revenue changed month by month and compare 2025 with 2024. Call out any seasonal patterns.
4. Break revenue down by product category and find the best-selling products (by quantity). Look at how the category mix changes through the year.
5. Compare categories on how often their orders are returned or canceled (by percent of total), and on average order value.
6. Create at least three clear, labeled charts that support your main points.
7. Finish with a one-page summary: three key findings and two recommendations for next year's plan.
## Plan (by Codex)

1. **Check and clean the data.** Review each file’s columns, types, duplicates, missing values, labels, and numeric ranges. Check that order and product IDs join correctly. Preserve the originals and record every correction, exclusion, and assumption in a cleaning log. Investigate missing prices before choosing how to handle them.
    
2. **Define revenue and metrics.** Proposed revenue: completed orders only, calculated as the sum of `quantity × unit_price − discount_amount`, assuming the discount is a line total. Confirm that assumption from the data. Exclude shipping from merchandise revenue and report it separately. Document how returned and canceled orders are treated.
    
3. **Compare monthly revenue.** Check date coverage first, then compare matching months in 2024 and 2025. Calculate monthly totals, year-over-year changes, completed-order counts, and average order value. Describe recurring peaks as possible seasonality, given only two years.
    
4. **Analyze categories and products.** Calculate category revenue and share, monthly category mix, and product rankings by completed-order quantity. Keep product IDs in rankings so similarly named products stay distinct.
    
5. **Compare category outcomes.** For each category, calculate returned and canceled orders as percentages of all distinct orders containing that category. Calculate category AOV as completed category revenue divided by completed orders containing that category. Explain that orders containing several categories appear in each relevant category.
    
6. **Create clear charts.** Use at least three:
    
    - Monthly revenue: 2024 versus 2025.
    - Monthly category revenue share.
    - Best-selling products by quantity.
    - Category return and cancellation rates, with order counts.
7. **Write and validate the conclusions.** Reconcile monthly, category, and order totals. Produce a one-page summary with exactly three evidence-based findings and two recommendations for the following year.
    

Proposed deliverables: a reproducible analysis notebook, a cleaning and methodology log, labeled charts, and the one-page summary. Cleaned record-level data would stay under the ignored `data/` directory.