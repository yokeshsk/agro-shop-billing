# Agro Shop Billing and Stock Management System

A beginner-friendly Python Flask project based on the project report for B25CEP301 – Concept for Practices I.

## Features
- Product management: name, category, price, quantity, batch number, expiry date and low-stock limit
- Billing with automatic totals and stock reduction
- Farmer records and credit sales
- Record credit repayments and view balances
- Low-stock and near-expiry alerts
- Daily sales summary and best-selling product report
- SQLite database created automatically with sample products on first run

## Requirements
- Python 3.10 or newer
- VS Code (recommended)
- Git (for GitHub)

## Run on Windows
Open this folder in VS Code, then open Terminal > New Terminal and run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, use Command Prompt terminal and run:

```bat
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser. Stop the server with `Ctrl+C` in the terminal.

## First steps to test
1. Open Products and add a product with quantity and expiry date.
2. Add a farmer under Farmers.
3. Open Billing, add product quantities and choose how much was paid.
4. For a credit sale, select a farmer and enter a paid amount below the bill total.
5. Open the bill to review it; stock is reduced after a successful sale.
6. Open Alerts and Reports to review stock warnings and sales.

## Database and sample data
The SQLite file `agro_shop.db` is created automatically when the app starts. Four sample products are inserted on the first run. The database file is ignored by Git so local shop/customer data is not accidentally published.

## Important limitations
This is an academic prototype, not production-ready billing or tax software. It does not yet implement user login/roles, compliant GST invoice numbering, barcode scanning, PDF printing, automated backups, or deployment security. Validate tax and record-keeping rules with a qualified person before real business use. Do not upload real customer phone numbers, credit records, credentials, or the database to a public GitHub repository.

## Project mapping to the report
- FR1: Product search and display of rate/stock/batch
- FR2: Bill with automatic total (tax calculation can be added after requirements are confirmed)
- FR3: Stock reduction after a sale
- FR4: Low-stock and expiry alerts
- FR5: Credit ledger linked to bills and payments
- FR6: Daily sales and top-product reports
