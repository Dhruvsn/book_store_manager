import boto3
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from botocore.exceptions import ClientError
from decimal import Decimal

app = Flask(__name__)
app.secret_key = 'your_bookstore_secret_key'

# --- AWS CONFIGURATION ---
# Using boto3 to connect to DynamoDB and SNS
dynamodb = boto3.resource('dynamodb', region_name='us-east-1') # Update to your region
sns = boto3.client('sns', region_name='us-east-1')

# Tables must be created in AWS Console first
USER_TABLE = dynamodb.Table('Users')
BOOK_TABLE = dynamodb.Table('Books')
ORDER_TABLE = dynamodb.Table('Orders')
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:123456789012:OrderNotifications' # Update with your ARN

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- HELPERS ---
def send_order_notification(username, total):
    try:
        message = f"New Order Placed!\nUser: {username}\nTotal: ${total}\nCheck the Admin Dashboard for details."
        sns.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject="Bookstore Order Alert")
    except Exception as e:
        print(f"SNS Error: {e}")

# --- CUSTOMER AUTHENTICATION ---

@app.route('/')
def home():
    try:
        book_count = BOOK_TABLE.scan(Select='COUNT')['Count']
        return render_template('home.html', stats={"book_count": book_count})
    except:
        return render_template('home.html', stats={"book_count": 0})

@app.route('/shop')
def index():
    response = BOOK_TABLE.scan()
    all_books = response.get('Items', [])
    return render_template('index.html', all_books=all_books)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        
        # Check if user exists
        existing = USER_TABLE.get_item(Key={'username': username}).get('Item')
        if existing:
            flash("User already exists!")
            return redirect(url_for('register'))
        
        USER_TABLE.put_item(Item={'username': username, 'password': password, 'role': 'customer'})
        flash("Registration successful!")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = USER_TABLE.get_item(Key={'username': username}).get('Item')
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['role'] = user.get('role', 'customer')
            return redirect(url_for('home'))
        flash("Invalid credentials!")
    return render_template('login.html')

# --- BOOKSTORE LOGIC ---

@app.route('/add_to_cart/<string:book_id>')
def add_to_cart(book_id):
    if 'username' not in session: return redirect(url_for('login'))
    
    if 'cart' not in session: session['cart'] = []
    session['cart'].append(book_id)
    session.modified = True
    flash("Added to cart!")
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart():
    if 'username' not in session: return redirect(url_for('login'))
    
    cart_ids = session.get('cart', [])
    cart_items = []
    total = Decimal('0.00')
    
    for bid in cart_ids:
        book = BOOK_TABLE.get_item(Key={'book_id': bid}).get('Item')
        if book:
            cart_items.append(book)
            total += Decimal(str(book['price']))
            
    return render_template('cart.html', items=cart_items, total=total)

@app.route('/place_order', methods=['POST'])
def place_order():
    username = session.get('username')
    cart_ids = session.get('cart', [])
    if not username or not cart_ids: return redirect(url_for('index'))
    
    total = Decimal('0.00')
    book_titles = []
    for bid in cart_ids:
        book = BOOK_TABLE.get_item(Key={'book_id': bid}).get('Item')
        if book:
            total += Decimal(str(book['price']))
            book_titles.append(book['title'])

    order_id = str(os.urandom(4).hex())
    ORDER_TABLE.put_item(Item={
        'order_id': order_id,
        'username': username,
        'book_list': book_titles,
        'total': total,
        'status': 'Success'
    })
    
    send_order_notification(username, total)
    session['cart'] = []
    flash("Order placed successfully!")
    return redirect(url_for('my_orders'))

@app.route('/my_orders')
def my_orders():
    if 'username' not in session: return redirect(url_for('login'))
    username = session['username']
    
    # Simple scan for user's orders (In production, use a Global Secondary Index)
    response = ORDER_TABLE.scan()
    user_orders = [o for o in response.get('Items', []) if o['username'] == username]
    return render_template('orders.html', orders=user_orders)

# --- ADMIN ROUTES ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Checking against 'admin' role in Users table
        user = USER_TABLE.get_item(Key={'username': username}).get('Item')
        if user and user.get('role') == 'admin' and check_password_hash(user['password'], password):
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        flash("Admin Access Denied!")
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session: return redirect(url_for('admin_login'))
    
    all_orders = ORDER_TABLE.scan().get('Items', [])
    all_books = BOOK_TABLE.scan().get('Items', [])
    all_users = USER_TABLE.scan().get('Items', [])
    
    return render_template('admin.html', 
                           all_orders=all_orders, 
                           all_books=all_books,
                           all_users=[u['username'] for u in all_users])

@app.route('/admin/add_book', methods=['POST'])
def admin_add_book():
    if 'admin' not in session: return redirect(url_for('admin_login'))
    
    book_id = str(os.urandom(4).hex())
    image = request.files.get('image')
    image_filename = "default.jpg"
    
    if image:
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    BOOK_TABLE.put_item(Item={
        'book_id': book_id,
        'title': request.form['title'],
        'author': request.form['author'],
        'price': Decimal(request.form['price']),
        'stock': int(request.form['stock']),
        'image': image_filename
    })
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    # host='0.0.0.0' allows external AWS access
    app.run(debug=True, host='0.0.0.0', port=5000)