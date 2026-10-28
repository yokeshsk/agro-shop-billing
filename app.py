from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import date, timedelta
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-before-deployment"
DB_PATH = Path(__file__).with_name("agro_shop.db")


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
            batch_no TEXT DEFAULT '',
            expiry_date TEXT DEFAULT '',
            low_stock_limit INTEGER NOT NULL DEFAULT 5
        );
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER,
            bill_date TEXT NOT NULL,
            total REAL NOT NULL,
            paid REAL NOT NULL,
            credit REAL NOT NULL,
            FOREIGN KEY(farmer_id) REFERENCES farmers(id)
        );
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL,
            FOREIGN KEY(bill_id) REFERENCES bills(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS credit_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            payment_date TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            note TEXT DEFAULT '',
            FOREIGN KEY(farmer_id) REFERENCES farmers(id)
        );
        """)
        count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            db.executemany("""INSERT INTO products
                (name, category, price, quantity, batch_no, expiry_date, low_stock_limit)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", [
                ("Neem Oil", "Pesticide", 250, 20, "NO-101", "2027-08-30", 5),
                ("Urea Fertiliser", "Fertiliser", 320, 40, "UF-202", "2028-01-31", 8),
                ("Paddy Seeds", "Seeds", 180, 25, "PS-303", "2027-04-30", 5),
                ("Organic Manure", "Manure", 150, 15, "OM-404", "2027-02-15", 4),
            ])


@app.route('/')
def dashboard():
    with connect_db() as db:
        products = db.execute("SELECT * FROM products ORDER BY name").fetchall()
        today_sales = db.execute("SELECT COALESCE(SUM(total),0) FROM bills WHERE bill_date=?", (date.today().isoformat(),)).fetchone()[0]
        today_bills = db.execute("SELECT COUNT(*) FROM bills WHERE bill_date=?", (date.today().isoformat(),)).fetchone()[0]
        low_count = db.execute("SELECT COUNT(*) FROM products WHERE quantity <= low_stock_limit").fetchone()[0]
        farmers = db.execute("SELECT COUNT(*) FROM farmers").fetchone()[0]
        credit = db.execute("SELECT COALESCE(SUM(credit),0) FROM bills").fetchone()[0] - db.execute("SELECT COALESCE(SUM(amount),0) FROM credit_payments").fetchone()[0]
    return render_template('dashboard.html', products=products, today_sales=today_sales, today_bills=today_bills, low_count=low_count, farmers=farmers, credit=max(0, credit))


@app.route('/products', methods=['GET', 'POST'])
def products_page():
    with connect_db() as db:
        if request.method == 'POST':
            try:
                name = request.form['name'].strip()
                category = request.form['category'].strip()
                price = float(request.form['price'])
                quantity = int(request.form['quantity'])
                low_limit = int(request.form.get('low_stock_limit') or 5)
                if not name or not category or price < 0 or quantity < 0 or low_limit < 0:
                    raise ValueError
                db.execute("""INSERT INTO products(name,category,price,quantity,batch_no,expiry_date,low_stock_limit)
                    VALUES(?,?,?,?,?,?,?)""", (name, category, price, quantity, request.form.get('batch_no','').strip(), request.form.get('expiry_date',''), low_limit))
                flash('Product added successfully.', 'success')
            except (ValueError, KeyError):
                flash('Please enter valid product details. Price and stock cannot be negative.', 'error')
            return redirect(url_for('products_page'))
        search = request.args.get('q', '').strip()
        rows = db.execute("SELECT * FROM products WHERE name LIKE ? OR category LIKE ? ORDER BY name", (f'%{search}%', f'%{search}%')).fetchall()
    return render_template('products.html', products=rows, search=search)


@app.route('/products/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    with connect_db() as db:
        used = db.execute('SELECT COUNT(*) FROM bill_items WHERE product_id=?', (product_id,)).fetchone()[0]
        if used:
            flash('This product is used in an old bill, so it cannot be deleted. Set its stock to zero instead.', 'error')
        else:
            db.execute('DELETE FROM products WHERE id=?', (product_id,))
            flash('Product deleted.', 'success')
    return redirect(url_for('products_page'))


@app.route('/farmers', methods=['GET', 'POST'])
def farmers_page():
    with connect_db() as db:
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            if name:
                db.execute('INSERT INTO farmers(name,phone) VALUES(?,?)', (name, phone))
                flash('Farmer added.', 'success')
            else:
                flash('Farmer name is required.', 'error')
            return redirect(url_for('farmers_page'))
        farmers = db.execute('''SELECT f.*,
            COALESCE((SELECT SUM(credit) FROM bills b WHERE b.farmer_id=f.id),0) -
            COALESCE((SELECT SUM(amount) FROM credit_payments p WHERE p.farmer_id=f.id),0) AS balance
            FROM farmers f ORDER BY f.name''').fetchall()
    return render_template('farmers.html', farmers=farmers)


@app.route('/credit/<int:farmer_id>', methods=['GET', 'POST'])
def credit_page(farmer_id):
    with connect_db() as db:
        farmer = db.execute('SELECT * FROM farmers WHERE id=?', (farmer_id,)).fetchone()
        if farmer is None:
            flash('Farmer not found.', 'error')
            return redirect(url_for('farmers_page'))
        if request.method == 'POST':
            try:
                amount = float(request.form['amount'])
                if amount <= 0:
                    raise ValueError
                db.execute('INSERT INTO credit_payments(farmer_id,payment_date,amount,note) VALUES(?,?,?,?)', (farmer_id, date.today().isoformat(), amount, request.form.get('note','').strip()))
                flash('Payment recorded.', 'success')
            except (ValueError, KeyError):
                flash('Enter a payment amount greater than zero.', 'error')
            return redirect(url_for('credit_page', farmer_id=farmer_id))
        bills = db.execute('SELECT * FROM bills WHERE farmer_id=? ORDER BY id DESC', (farmer_id,)).fetchall()
        payments = db.execute('SELECT * FROM credit_payments WHERE farmer_id=? ORDER BY id DESC', (farmer_id,)).fetchall()
        total_credit = sum(row['credit'] for row in bills)
        total_paid = sum(row['amount'] for row in payments)
    return render_template('credit.html', farmer=farmer, bills=bills, payments=payments, balance=max(0, total_credit-total_paid), total_credit=total_credit, total_paid=total_paid)


@app.route('/billing', methods=['GET', 'POST'])
def billing_page():
    with connect_db() as db:
        if request.method == 'POST':
            try:
                farmer_id = request.form.get('farmer_id') or None
                paid = float(request.form.get('paid') or 0)
                product_ids = request.form.getlist('product_id')
                quantities = request.form.getlist('quantity')
                items = []
                total = 0.0
                for pid, qty_text in zip(product_ids, quantities):
                    qty = int(qty_text)
                    if qty <= 0:
                        continue
                    product = db.execute('SELECT * FROM products WHERE id=?', (int(pid),)).fetchone()
                    if product is None or product['quantity'] < qty:
                        raise ValueError('A selected product is unavailable or has insufficient stock.')
                    line_total = product['price'] * qty
                    total += line_total
                    items.append((product, qty, line_total))
                if not items:
                    raise ValueError('Add at least one product with quantity greater than zero.')
                if paid < 0 or paid > total:
                    raise ValueError('Paid amount must be between zero and the bill total.')
                credit = total - paid
                if credit > 0 and not farmer_id:
                    raise ValueError('Select a farmer for a credit sale.')
                db.execute('BEGIN')
                cursor = db.execute('INSERT INTO bills(farmer_id,bill_date,total,paid,credit) VALUES(?,?,?,?,?)', (int(farmer_id) if farmer_id else None, date.today().isoformat(), total, paid, credit))
                bill_id = cursor.lastrowid
                for product, qty, line_total in items:
                    db.execute('INSERT INTO bill_items(bill_id,product_id,product_name,quantity,unit_price,line_total) VALUES(?,?,?,?,?,?)', (bill_id, product['id'], product['name'], qty, product['price'], line_total))
                    db.execute('UPDATE products SET quantity=quantity-? WHERE id=?', (qty, product['id']))
                db.commit()
                flash(f'Bill #{bill_id} created. Total: ₹{total:.2f}', 'success')
                return redirect(url_for('bill_detail', bill_id=bill_id))
            except (ValueError, TypeError, KeyError) as exc:
                db.rollback()
                flash(str(exc) or 'Please check the billing details.', 'error')
                return redirect(url_for('billing_page'))
        products = db.execute('SELECT * FROM products WHERE quantity > 0 ORDER BY name').fetchall()
        farmers = db.execute('SELECT * FROM farmers ORDER BY name').fetchall()
    return render_template('billing.html', products=products, farmers=farmers)


@app.route('/bills/<int:bill_id>')
def bill_detail(bill_id):
    with connect_db() as db:
        bill = db.execute('SELECT b.*, f.name AS farmer_name FROM bills b LEFT JOIN farmers f ON f.id=b.farmer_id WHERE b.id=?', (bill_id,)).fetchone()
        if bill is None:
            flash('Bill not found.', 'error')
            return redirect(url_for('reports_page'))
        items = db.execute('SELECT * FROM bill_items WHERE bill_id=?', (bill_id,)).fetchall()
    return render_template('bill_detail.html', bill=bill, items=items)


@app.route('/reports')
def reports_page():
    with connect_db() as db:
        bills = db.execute('''SELECT b.*, f.name AS farmer_name FROM bills b LEFT JOIN farmers f ON f.id=b.farmer_id ORDER BY b.id DESC LIMIT 100''').fetchall()
        today_total = db.execute('SELECT COALESCE(SUM(total),0) FROM bills WHERE bill_date=?', (date.today().isoformat(),)).fetchone()[0]
        all_total = db.execute('SELECT COALESCE(SUM(total),0) FROM bills').fetchone()[0]
        top_products = db.execute('''SELECT product_name, SUM(quantity) AS units, SUM(line_total) AS sales FROM bill_items GROUP BY product_name ORDER BY units DESC LIMIT 5''').fetchall()
        credit_total = db.execute('SELECT COALESCE(SUM(credit),0) FROM bills').fetchone()[0] - db.execute('SELECT COALESCE(SUM(amount),0) FROM credit_payments').fetchone()[0]
    return render_template('reports.html', bills=bills, today_total=today_total, all_total=all_total, top_products=top_products, credit_total=max(0,credit_total))


@app.route('/alerts')
def alerts_page():
    today = date.today()
    expiry_limit = (today + timedelta(days=30)).isoformat()
    with connect_db() as db:
        low = db.execute('SELECT * FROM products WHERE quantity <= low_stock_limit ORDER BY quantity').fetchall()
        expiry = db.execute("SELECT * FROM products WHERE expiry_date <> '' AND expiry_date <= ? ORDER BY expiry_date", (expiry_limit,)).fetchall()
    return render_template('alerts.html', low=low, expiry=expiry, today=today.isoformat(), expiry_limit=expiry_limit)


init_db()

if __name__ == '__main__':
    app.run(debug=True)
