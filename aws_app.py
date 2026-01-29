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
# DynamoDB and SNS initialization (Make sure your EC2 has an IAM Role attached)
dynamodb = boto3.resource('dynamodb', region_name='us-east-1') 
sns = boto3.client('sns', region_name='us-east-1')

USER_TABLE = dynamodb.Table('Users')
BOOK_TABLE = dynamodb.Table('Books')
ORDER_TABLE = dynamodb.Table('Orders')
SNS_TOPIC_ARN = 'your_sns_topic_arn_here' # Replace with your ARN

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- HELPERS ---
def send_order_notification(username, total):
    try:
        message = f"New Order Placed!\nUser: {username}\nTotal: ${total}\nCheck the Admin Dashboard."
        sns.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject="Bookstore Order Alert")
    except Exception as e:
        print(f"SNS Error: {e}")

# --- AUTHENTICATION ROUTES ---

@app.route('/signup', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        try:
            USER_TABLE.put_item(Item={'username': username, 'password': password, 'role': 'customer'})
            flash("Registration successful!")
            return redirect(url_for('login'))
        except ClientError:
            flash("Database Connection Error")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = USER_TABLE.get_item(Key={'username': username}).get('Item')
        
        if user and check_password_hash(user['password'], password):
            if user.get('role') == 'admin':
                session['admin'] = username
                return redirect(url_for('admin_dashboard'))
            else:
                session['username'] = username
                return redirect(url_for('index'))
        flash("Invalid credentials!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Logged out.")
    return redirect(url_for('home'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash("Admin logged out.")
    return redirect(url_for('home'))

# --- CUSTOMER STORE ROUTES ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/shop')
def index():
    response = BOOK_TABLE.scan()
    all_books = response.get('Items', [])
    return render_template('index.html', all_books=all_books)

@app.route('/add_to_cart/<string:book_id>')
def add_to_cart(book_id):
    if 'username' not in session: return redirect(url_for('login'))
    if 'cart' not in session: session['cart'] = []
    session['cart'].append(book_id)
    session.modified = True
    flash("Added to cart!")
    return redirect(url_for('index'))

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
    return redirect(url_for('home'))

# --- ADMIN DASHBOARD ---

@app.route('/admin')
def admin_dashboard():
    if 'admin' not in session: return redirect(url_for('login'))
    all_orders = ORDER_TABLE.scan().get('Items', [])
    all_books = BOOK_TABLE.scan().get('Items', [])
    all_users = USER_TABLE.scan().get('Items', [])
    return render_template('admin.html', all_orders=all_orders, all_books=all_books, all_users=all_users)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    session.pop('username', None)
    flash("Admin session ended safely.")
    return redirect(url_for('home'))

@app.route('/admin/add_book', methods=['POST'])
def admin_add_book():
    if 'admin' not in session: return redirect(url_for('login'))
    book_id = str(os.urandom(4).hex())
    image = request.files.get('image')
    filename = secure_filename(image.filename) if image else "default.jpg"
    if image: image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    BOOK_TABLE.put_item(Item={
        'book_id': book_id,
        'title': request.form['title'],
        'author': request.form['author'],
        'price': Decimal(request.form['price']),
        'stock': int(request.form['stock']),
        'image': filename
    })
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)