import sqlite3
import pandas as pd
import logging
from ingestion_db import ingest_db

logger = logging.getLogger("get_vendor_summary")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    file_handler = logging.FileHandler("logs/get_vendor_summary.log", mode = "a")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def create_vendor_summary(conn):
    '''Merge diffrent tables to get the overall vendor summary and adding new columns'''
    
    vendor_sales_summary = pd.read_sql_query("""
        with FreightSummary as (
            select VendorNumber, SUM(Freight) as FreightCost
            from vendor_invoice
            group by VendorNumber
        ),
        PurchaseSummary as (
            select
                p.VendorNumber,
                p.VendorName,
                p.Brand,
                p.Description,
                p.PurchasePrice,
                pp.Price as ActualPrice,
                pp.Volume,
                SUM(p.Quantity) as TotalPurchaseQuantity,
                SUM(p.Dollars) as TotalPurchaseDollars
            from purchases p
            join purchase_prices pp
            on p.Brand = pp.Brand
            where p.PurchasePrice > 0
            group by p.VendorNumber, p.VendorName, p.Brand, p.Description, p.PurchasePrice, pp.Price, pp.Volume
        ),
        SalesSummary as (
            select
                VendorNo,
                Brand,
                SUM(SalesQuantity) as TotalSalesQuantity,
                SUM(SalesDollars) as TotalSalesDollars,
                SUM(SalesPrice) as TotalSalesPrice,
                SUM(ExciseTax) as TotalExciseTax
            from sales
            group by VendorNo, Brand
        )
        select
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
        from PurchaseSummary ps
        left join SalesSummary ss
            on ps.VendorNumber = ss.VendorNo
            and ps.Brand = ss.Brand
        left join FreightSummary fs
            on ps.VendorNumber = fs.VendorNumber
        order by ps.TotalPurchaseDollars desc
        """, conn)
    
    return vendor_sales_summary

def clean_df(df):
    '''Cleaning the data'''
    
    df['Volume'] = df['Volume'].astype('float')
    
    df.fillna(0, inplace=True)
    
    df['VendorName'] = df['VendorName'].str.strip()
    df['Description'] = df['Description'].str.strip()
    
    df['GrossProfit'] = df['TotalSalesDollars'] - df['TotalPurchaseDollars']
    df['ProfitMargin'] = (df['GrossProfit'] / df['TotalSalesDollars']) * 100
    df['StockTurnover'] = df['TotalSalesQuantity'] / df['TotalPurchaseQuantity'] 
    df['SalesToPurchaseRatio'] = df['TotalSalesDollars'] / df['TotalPurchaseDollars']
    
    return df

if __name__ == "__main__":
    conn = sqlite3.connect('inventory.db')
    logger.info("Creating Vendor Summary Table...")
    summary_df = create_vendor_summary(conn)
    logger.info(summary_df.head())
    
    logger.info("Cleaning Data...")
    cleaned_df = clean_df(summary_df)
    logger.info(cleaned_df.head())
    
    logger.info("Ingesting Data...")
    ingest_db(cleaned_df, 'vendor_sales_summary', conn)
    logger.info("Completed")
