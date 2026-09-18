import sqlite3
import pandas as pd
import logging
import os
import time


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/get_vendor_summary.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)


# ============================================================
# CREATE VENDOR SUMMARY
# ============================================================

def create_vendor_summary(conn):
    """
    Merge purchase, sales and freight data
    to create the overall vendor sales summary.
    """

    start_time = time.time()

    logging.info("========================================")
    logging.info("Starting vendor summary creation")
    logging.info("========================================")

    try:

        logging.info("Creating Freight Summary")

        vendor_sales_summary = pd.read_sql_query(
            """
            WITH FreightSummary AS (

                SELECT
                    VendorNumber,
                    SUM(Freight) AS FreightCost

                FROM vendor_invoice

                GROUP BY VendorNumber
            ),

            PurchaseSummary AS (

                SELECT
                    p.VendorNumber,
                    p.VendorName,
                    p.Brand,
                    p.Description,
                    p.PurchasePrice,
                    pp.Price AS ActualPrice,
                    pp.Volume,

                    SUM(p.Quantity) AS TotalPurchaseQuantity,
                    SUM(p.Dollars) AS TotalPurchaseDollars

                FROM purchases p

                JOIN purchase_prices pp
                    ON p.Brand = pp.Brand

                WHERE p.PurchasePrice > 0

                GROUP BY
                    p.VendorNumber,
                    p.VendorName,
                    p.Brand,
                    p.Description,
                    p.PurchasePrice,
                    pp.Price,
                    pp.Volume
            ),

            SalesSummary AS (

                SELECT
                    VendorNo,
                    Brand,

                    SUM(SalesQuantity) AS TotalSalesQuantity,
                    SUM(SalesDollars) AS TotalSalesDollars,
                    SUM(SalesPrice) AS TotalSalesPrice,
                    SUM(ExciseTax) AS TotalExciseTax

                FROM sales

                GROUP BY
                    VendorNo,
                    Brand
            )

            SELECT

                ps.VendorNumber,
                ps.VendorName,
                ps.Brand,
                ps.Description,
                ps.PurchasePrice,
                ps.ActualPrice,
                ps.Volume,

                ps.TotalPurchaseQuantity,
                ps.TotalPurchaseDollars,

                ss.TotalSalesQuantity,
                ss.TotalSalesDollars,
                ss.TotalSalesPrice,
                ss.TotalExciseTax,

                fs.FreightCost

            FROM PurchaseSummary ps

            LEFT JOIN SalesSummary ss
                ON ps.VendorNumber = ss.VendorNo
                AND ps.Brand = ss.Brand

            LEFT JOIN FreightSummary fs
                ON ps.VendorNumber = fs.VendorNumber

            ORDER BY
                ps.TotalPurchaseDollars DESC
            """,
            conn
        )

        logging.info(
            f"Vendor summary created successfully. "
            f"Rows: {len(vendor_sales_summary)}"
        )

        logging.info("Vendor summary columns:")
        logging.info(
            list(vendor_sales_summary.columns)
        )

        # ====================================================
        # DATA CLEANING
        # ====================================================

        logging.info("Starting data cleaning")

        vendor_sales_summary["Volume"] = pd.to_numeric(
            vendor_sales_summary["Volume"],
            errors="coerce"
        )

        logging.info("Converted Volume column to numeric")

        # Fill missing values
        vendor_sales_summary.fillna(
            0,
            inplace=True
        )

        logging.info("Filled missing values with 0")

        # Remove spaces from VendorName
        vendor_sales_summary["VendorName"] = (
            vendor_sales_summary["VendorName"]
            .astype(str)
            .str.strip()
        )

        logging.info(
            "Removed leading and trailing spaces "
            "from VendorName"
        )

        # Remove spaces from Description
        vendor_sales_summary["Description"] = (
            vendor_sales_summary["Description"]
            .astype(str)
            .str.strip()
        )

        logging.info(
            "Removed leading and trailing spaces "
            "from Description"
        )

        # ====================================================
        # CREATE NEW METRICS
        # ====================================================

        logging.info("Creating calculated columns")

        # Gross Profit
        vendor_sales_summary["GrossProfit"] = (
            vendor_sales_summary["TotalSalesDollars"]
            - vendor_sales_summary["TotalPurchaseDollars"]
        )

        logging.info("GrossProfit calculated")

        # Profit Margin
        vendor_sales_summary["ProfitMargin"] = 0.0

        mask = (
            vendor_sales_summary["TotalSalesDollars"] != 0
        )

        vendor_sales_summary.loc[mask, "ProfitMargin"] = (
            vendor_sales_summary.loc[
                mask,
                "GrossProfit"
            ]
            /
            vendor_sales_summary.loc[
                mask,
                "TotalSalesDollars"
            ]
            * 100
        )

        logging.info("ProfitMargin calculated")

        # Stock Turnover
        vendor_sales_summary["StockTurnover"] = 0.0

        mask = (
            vendor_sales_summary["TotalPurchaseQuantity"] != 0
        )

        vendor_sales_summary.loc[
            mask,
            "StockTurnover"
        ] = (
            vendor_sales_summary.loc[
                mask,
                "TotalSalesQuantity"
            ]
            /
            vendor_sales_summary.loc[
                mask,
                "TotalPurchaseQuantity"
            ]
        )

        logging.info("StockTurnover calculated")

        # Sales to Purchase Ratio
        vendor_sales_summary["SalesToPurchaseRatio"] = 0.0

        mask = (
            vendor_sales_summary["TotalPurchaseDollars"] != 0
        )

        vendor_sales_summary.loc[
            mask,
            "SalesToPurchaseRatio"
        ] = (
            vendor_sales_summary.loc[
                mask,
                "TotalSalesDollars"
            ]
            /
            vendor_sales_summary.loc[
                mask,
                "TotalPurchaseDollars"
            ]
        )

        logging.info(
            "SalesToPurchaseRatio calculated"
        )

        # ====================================================
        # DATA QUALITY CHECK
        # ====================================================

        logging.info("Running data quality checks")

        missing_values = (
            vendor_sales_summary.isnull().sum().sum()
        )

        logging.info(
            f"Remaining missing values: {missing_values}"
        )

        logging.info(
            f"Final dataframe shape: "
            f"{vendor_sales_summary.shape}"
        )

        # ====================================================
        # FINISH
        # ====================================================

        end_time = time.time()

        total_time = (end_time - start_time) / 60

        logging.info(
            f"Vendor summary creation completed "
            f"in {total_time:.2f} minutes"
        )

        logging.info("========================================")
        logging.info("Vendor Summary Completed")
        logging.info("========================================")

        return vendor_sales_summary

    except Exception as e:

        logging.error(
            "Error while creating vendor summary",
            exc_info=True
        )

        raise e


# ============================================================
# MAIN PROGRAM
# ============================================================

if __name__ == "__main__":

    logging.info("Starting get_vendor_summary.py")

    try:

        # Connect to SQLite database
        conn = sqlite3.connect("inventory.db")

        logging.info(
            "Connected to inventory.db"
        )

        # Create vendor summary
        summary_df = create_vendor_summary(conn)

        logging.info(
            "Vendor summary dataframe created"
        )

        # Display first 5 rows
        print(summary_df.head())

        # Save summary to SQLite
        summary_df.to_sql(
            "vendor_sales_summary",
            conn,
            if_exists="replace",
            index=False
        )

        logging.info(
            "vendor_sales_summary table saved to database"
        )

        # Close connection
        conn.close()

        logging.info(
            "Database connection closed"
        )

        logging.info(
            "get_vendor_summary.py completed successfully"
        )

        print(
            "\nVendor summary completed successfully."
        )

    except Exception as e:

        logging.error(
            "Program failed",
            exc_info=True
        )

        print(
            f"\nError: {e}"
        )