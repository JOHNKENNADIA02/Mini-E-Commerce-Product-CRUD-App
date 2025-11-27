from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import os
import config  # Import your config file

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create folder if it doesn't exist

# # ===========================
# # MySQL Connection
# # ===========================
def get_db_connection():
    """Return a MySQL connection using config.py settings."""
    try:
        conn = mysql.connector.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DB
        )
        return conn
    except mysql.connector.Error as err:
        print("Error connecting to MySQL:", err)
        return None
    

# ===========================
# USER ROUTES
# ===========================
@app.route('/')
def index():
    products = []  # default empty list
    db = None
    cursor = None

    try:
        # Attempt to connect to database
        db = get_db_connection()
        if db is None:
            raise Exception("Database connection failed")

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products LIMIT 3")
        products = cursor.fetchall()

    except Exception as e:
        print("Error:", e)  # print full error
        # Optionally flash a message to the user
        # flash("Unable to load products at this time", "danger")

    finally:
        # Safely close cursor and connection
        if cursor:
            cursor.close()
        if db:
            db.close()

    return render_template('index.html', products=products)




@app.route('/products')
def products():
    db = get_db_connection()
    if not db:
        # If connection fails, show an error page or empty list
        flash("Database connection failed", "danger")
        return render_template('products.html', products=[])

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('products.html', products=products)

@app.route('/product/<int:id>')
def product_details(id):
    db = get_db_connection()
    if not db:
        flash("Database connection failed", "danger")
        return redirect(url_for('products'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()
    cursor.close()
    db.close()

    if not product:
        flash("Product not found", "danger")
        return redirect(url_for('products'))

    return render_template('product-details.html', product=product)


# ===========================
# ADMIN ROUTES
# ===========================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    db = get_db_connection()
    if not db:
        flash("Database connection failed", "danger")
        return render_template('admin/login.html')

    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM admin_users WHERE username=%s", (username,))
        admin = cursor.fetchone()

        if admin and password == admin['password_hash']:  # For real projects, use hashing
            cursor.close()
            db.close()
            return redirect(url_for('admin_list'))
        else:
            flash("Invalid username or password", "danger")

    cursor.close()
    db.close()
    return render_template('admin/login.html')


@app.route('/admin/list')
def admin_list():
    db = get_db_connection()
    if not db:
        flash("Database connection failed", "danger")
        return render_template('admin/list.html', products=[])

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('admin/list.html', products=products)


@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        short_desc = request.form['short_description']
        full_desc = request.form['full_description']

        # Handle file upload
        file = request.files.get('image')
        filename = None

        if file and file.filename != '':
            filename = file.filename
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)

        # Insert into database
        sql = """
            INSERT INTO products (name, price, short_description, full_description, image)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (name, price, short_desc, full_desc, filename))
        db.commit()

        cursor.close()
        db.close()

        flash("Product added successfully", "success")
        return redirect(url_for('admin_list'))

    cursor.close()
    db.close()

    return render_template('admin/add.html')


@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit(id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found", "danger")
        return redirect(url_for('admin_list'))

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        short_desc = request.form['short_description']
        full_desc = request.form['full_description']

        file = request.files.get('image')
        filename = product['image']

        if file and file.filename != '':
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        sql = """
            UPDATE products 
            SET name=%s, price=%s, short_description=%s, full_description=%s, image=%s 
            WHERE id=%s
        """

        cursor.execute(sql, (name, price, short_desc, full_desc, filename, id))
        db.commit()

        cursor.close()
        db.close()

        flash("Product updated successfully", "success")
        return redirect(url_for('admin_list'))

    cursor.close()
    db.close()

    return render_template('admin/edit.html', product=product)


@app.route('/admin/delete/<int:id>')
def admin_delete(id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # 1. Check product exists
    cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()

    if not product:
        cursor.close()
        db.close()
        flash("Product not found", "danger")
        return redirect(url_for('admin_list'))

    # 2. Delete image file if exists
    if product['image']:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image'])
        if os.path.exists(image_path):
            os.remove(image_path)

    # 3. Delete product from database
    cursor.execute("DELETE FROM products WHERE id=%s", (id,))
    db.commit()

    cursor.close()
    db.close()

    flash("Product deleted successfully", "success")
    return redirect(url_for('admin_list'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)  # Remove session variable
    flash("Logged out successfully", "success")
    return redirect(url_for('admin_login'))

# ===========================
# Run Flask
# ===========================
if __name__ == '__main__':
    app.run(debug=True)
