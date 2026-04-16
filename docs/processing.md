While these terms are often used interchangeably in casual conversation, they represent distinct stages in the data preparation pipeline. Think of it as preparing a meal: **cleaning** is washing the vegetables and removing the bruised parts, **transforming** is chopping or cooking them into a new form, and **standardizing** is ensuring every portion is the same size.

---

## 1. Data Cleaning
**The Goal:** Fix errors and remove "noise" so the data is accurate and usable.
Cleaning is the first line of defense. It deals with data that is broken, missing, or physically impossible.

* **Handling Missing Values:** Deciding whether to delete a row with a missing age or fill it with the average.
* **Removing Duplicates:** Ensuring the same customer isn't counted twice because they signed up with two different emails.
* **Fixing Structural Errors:** Correcting typos (e.g., "Mcrosoft" vs "Microsoft") or inconsistent capitalization.
* **Outlier Detection:** Identifying and investigating data points that seem impossible (e.g., a human height of 12 feet).

---

## 2. Data Transformation
**The Goal:** Change the format, structure, or values of data to make it better suited for analysis or machine learning models.
Transformation is a broad category. You aren't necessarily "fixing" a mistake; you are changing the data's "shape" to make it more useful.

* **Aggregation:** Turning daily sales data into a monthly total.
* **Encoding:** Converting categorical text (like "Red," "Green," "Blue") into numbers (0, 1, 2) so an algorithm can process it.
* **Feature Engineering:** Creating a new column, like "Is_Weekend," derived from a "Date" column.



---

## 3. Data Standardization
**The Goal:** Put different variables on the same scale so they can be compared fairly.
Standardization is actually a **specific type of transformation**. It is used when you have different units of measurement that might confuse a model.

* **The Problem:** If you are comparing "Income" (which ranges from $30,000 to $200,000) and "Age" (which ranges from 18 to 80), a machine learning model might think Income is "more important" simply because the numbers are larger.
* **The Solution:** You rescale both so they have a mean of 0 and a standard deviation of 1.
* **Normalization:** A similar concept where you squish all values into a specific range, usually between 0 and 1.



---

### Summary Table

| Process | Core Question | Example |
| :--- | :--- | :--- |
| **Cleaning** | Is the data "correct"? | Deleting a row where the "Price" is negative. |
| **Transforming** | Is the data in the right "format"? | Changing a "Birthdate" into an "Age" integer. |
| **Standardizing** | Is the data on the same "scale"? | Changing kilograms and pounds into a single scale from 0 to 1. |