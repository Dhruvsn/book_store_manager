# 📚 BookStore Manager

A professional E-commerce platform designed for technical literature, featuring a robust admin dashboard, secure customer authentication, and a cloud-integrated backend. This project is optimized for deployment on **AWS EC2** using **DynamoDB** for persistent storage and **SNS** for real-time notifications.

## 🚀 Features
* **Dual Authentication System**: Separate secure login portals for Customers and Administrators.
* **Persistent Cloud Storage**: Integrated with **Amazon DynamoDB** to ensure data (Users, Books, Orders) survives instance restarts.
* **Real-time Alerts**: Leverages **Amazon SNS** to notify administrators immediately when a new order is placed.
* **Admin Dashboard**: Full control over inventory management, including book creation with image uploads and a global order monitor.
* **Responsive Design**: Built with **Bootstrap 5** for a seamless experience across desktop and mobile devices.

## 🛠️ Tech Stack
* **Backend**: Python (Flask)
* **Cloud Provider**: AWS (EC2, DynamoDB, SNS)
* **Database**: Amazon DynamoDB (NoSQL)
* **Security**: Password hashing via Werkzeug
* **Frontend**: Jinja2 Templates, Bootstrap 5



---

## 📁 Project Structure
```text
BookStoreManager/
├── app.py              # Local development version (In-memory dicts)
├── aws_app.py          # Production version for AWS (DynamoDB/SNS)
├── requirements.txt    # Python dependencies
├── static/
│   └── uploads/        # Directory for book cover images
└── templates/
    ├── base.html       # Main layout with corrected conditional navbar
    ├── home.html       # Landing page with site information
    ├── index.html      # Book catalog (Shop)
    ├── login.html      # Authentication page
    ├── admin.html      # Admin management dashboard
    └── orders.html     # Customer order history


# ⚙️ Setup & Installation

### 1. Local Environment
**Install dependencies:**
```bash
pip install -r requirements.txt

Access: Open your browser to http://127.0.0.1:5000

# Credentials & Access
Default Admin: The admin account is pre-configured with the username admin and password admin123.

Security: All passwords are hashed before storage using werkzeug.security to ensure user privacy.