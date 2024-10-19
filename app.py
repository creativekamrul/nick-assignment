from flask import Flask, request, jsonify
import sqlite3
import os
import re

app = Flask(__name__)
DB_PATH = 'all-orders.db'

# Input validation rules
VALIDATION_RULES = {
    'customer_name': {
        'max_length': 100,
        'pattern': r'^[a-zA-Z0-9\s\.]+$',
        'error_msg': 'Customer name can only have letters, numbers, spaces and periods'
    },
    'item_name': {
        'max_length': 200,
        'pattern': r'^[a-zA-Z0-9\s\'"]+$',
        'error_msg': 'Item name can only have letters, numbers, spaces, and quotes'
    },
    'quantity': {
        'min': 1,
        'max': 1000,
        'error_msg': 'Quantity must be between 1 and 1000'
    },
    'total_price': {
        'min': 0.01,
        'max': 1000000.00,
        'error_msg': 'Total price must be between 0.01 and 1,000,000.00'
    }
}

# SQLite 3 to Py dicts
def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

# Creating/Connection to db
def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

# Sample Data
    cursor.execute('SELECT COUNT(*) FROM orders')
    if cursor.fetchone()[0] == 0:
        sample_orders = [
            ('Kamrul Islam', 'MSI Gaming Laptop', 1, 1299.99),
            ('Alif', 'Ajazz Ak870 Pro Keybaord', 2, 49.98),
            ('Fatema Tuz Johra', 'Dareu Ak950Pro Gaming Mouse', 1, 59.99),
            ('Riha', 'Walton Monitor 27 inche', 2, 599.98),
            ('Mehedi HasaN', 'USB-C Cable', 3, 29.97)
        ]

        cursor.executemany('''
            INSERT INTO orders (customer_name, item_name, quantity, total_price)
            VALUES (?, ?, ?, ?)
        ''', sample_orders)

    conn.commit()
    conn.close()

# Handling edge cases also using the input validations
def sanitize_string(value, field_name):
    errors = []
    rules = VALIDATION_RULES[field_name]
    
    if not isinstance(value, str):
        return None, [f'{field_name} should be a string']
    
    value = value.strip()
    
    if not value:
        return None, [f'{field_name} cannot be empty']
        
    if len(value) > rules['max_length']:
        errors.append(f'{field_name} cannot exceed {rules["max_length"]} characters')
        
    if not re.match(rules['pattern'], value):
        errors.append(rules['error_msg'])
    
    return value, errors

def validate_number(value, field_name):
    rules = VALIDATION_RULES[field_name]
    try:
        if field_name == 'quantity':
            num = int(value)
        else:
            num = float(value)
            num = round(num, 2)
            
        if num < rules['min'] or num > rules['max']:
            return None, [rules['error_msg']]
        return num, []
    except (ValueError, TypeError):
        return None, [f'Invalid {field_name} format']

def validate_order_data(data):
    if not isinstance(data, dict):
        return None, ['Invalid request format. Expected JSON object']

    required_fields = ['customer_name', 'item_name', 'quantity', 'total_price']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return None, [f'Missing required fields: {", ".join(missing_fields)}']

    validated_data = {}
    errors = []


    for field in ['customer_name', 'item_name']:
        value, field_errors = sanitize_string(data.get(field), field)
        if field_errors:
            errors.extend(field_errors)
        else:
            validated_data[field] = value


    for field in ['quantity', 'total_price']:
        value, field_errors = validate_number(data.get(field), field)
        if field_errors:
            errors.extend(field_errors)
        else:
            validated_data[field] = value

    if errors:
        return None, errors

    return validated_data, []

# API endpoints 
@app.route('/orders', methods=['GET'])
def get_orders():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
        orders = cursor.fetchall()
        
        return jsonify(orders)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch'}), 500
    finally:
        conn.close()

@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    try:
        if not order_id.isdigit():
            return jsonify({'error': 'Invalid order ID format'}), 400

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        return jsonify(order)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch details'}), 500
    finally:
        conn.close()

@app.route('/orders', methods=['POST'])
def create_order():
    conn = None
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No provided data'}), 400

        validated_data, errors = validate_order_data(data)
        
        if errors:
            return jsonify({'errors': errors}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO orders (customer_name, item_name, quantity, total_price)
            VALUES (?, ?, ?, ?)
        ''', (
            validated_data['customer_name'],
            validated_data['item_name'],
            validated_data['quantity'],
            validated_data['total_price']
        ))
        
        order_id = cursor.lastrowid
        conn.commit()

        return jsonify({
            'message': 'Order successfully created',
            'order_id': order_id
        }), 201

    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        return jsonify({'error': 'Failed to create the order'}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        init_database()
    
    print("Server Running on http://127.0.0.1:5000")
    
    app.run()