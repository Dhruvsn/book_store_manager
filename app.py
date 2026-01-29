from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "bookstore_secret_key"

# --- DATA STORAGE (IN-MEMORY) ---
users = {}   
books = {
    1: {"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "price": 10.99, "stock": 5},
    2: {"id": 2, "title": "Flutter in Action", "author": "Eric Windmill", "price": 40.00, "stock": 8},
    3: {"id": 3, "title": "Web3 & Cryptography", "author": "Digital Scholar", "price": 25.00, "stock": 10}
}
carts = {}   
orders = {}  

id_counters = {"user": 1, "book": 4, "order": 1}

# Default Admin Account
users[0] = {"id": 0, "username": "admin", "password": generate_password_hash("admin123"), "is_admin": True}

# --- ROUTES ---

@app.route('/')
def home():
    # Landing page entry point
    stats = {"book_count": len(books), "user_count": len(users)}
    return render_template('home.html', stats=stats)

@app.route('/shop')
def index():
    # Catalog view
    return render_template('index.html', all_books=books.values())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if any(u['username'] == username for u in users.values()):
            flash("Username already exists!")
            return redirect(url_for('register'))
        uid = id_counters["user"]
        users[uid] = {"id": uid, "username": username, "password": generate_password_hash(password), "is_admin": False}
        id_counters["user"] += 1
        flash("Registration successful! Please login.")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = next((u for u in users.values() if u['username'] == username), None)
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            
            flash(f"Welcome back, {username}!")
            
            # --- REDIRECTION LOGIC ---
            if user['is_admin']:
                return redirect(url_for('admin_dashboard')) # Go to Admin Dashboard
            return redirect(url_for('home')) # Regular users go Home
            
        flash("Invalid username or password.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/add_to_cart/<int:book_id>')
def add_to_cart(book_id):
    if 'user_id' not in session:
        flash("Please login first.")
        return redirect(url_for('login'))
    uid = session['user_id']
    if uid not in carts: carts[uid] = []
    carts[uid].append(book_id)
    flash("Added to cart!")
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    user_cart_ids = carts.get(uid, [])
    cart_items = [books[bid] for bid in user_cart_ids]
    total = sum(item['price'] for item in cart_items)
    return render_template('cart.html', items=cart_items, total=total)

@app.route('/place_order', methods=['POST'])
def place_order():
    uid = session.get('user_id')
    if not uid or not carts.get(uid): return redirect(url_for('index'))
    user_cart = carts[uid]
    total = sum(books[bid]['price'] for bid in user_cart)
    oid = id_counters["order"]
    
    # Using 'book_list' to avoid Jinja2 .items() conflict
    orders[oid] = {
        "id": oid,
        "user_id": uid,
        "book_list": [books[bid]['title'] for bid in user_cart],
        "total": round(total, 2),
        "status": "Success"
    }
    id_counters["order"] += 1
    carts[uid] = []
    flash("Order placed successfully!")
    return redirect(url_for('my_orders'))

@app.route('/my_orders')
def my_orders():
    uid = session.get('user_id')
    user_orders = [o for o in orders.values() if o['user_id'] == uid]
    return render_template('orders.html', orders=user_orders)

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'): return "Access Denied", 403
    return render_template('admin.html', all_orders=orders.values(), all_books=books.values())

@app.route('/admin/logout')
def admin_logout():
    session.clear() # Clears both 'username' and 'is_admin'
    flash("Admin logged out successfully.")
    return redirect(url_for('home'))

@app.route('/admin/add_book', methods=['POST'])
def add_book():
    if not session.get('is_admin'): return redirect(url_for('index'))
    bid = id_counters["book"]
    books[bid] = {
        "id": bid,
        "title": request.form.get('title'),
        "author": request.form.get('author'),
        "price": float(request.form.get('price')),
        "stock": int(request.form.get('stock'))
    }
    id_counters["book"] += 1
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)