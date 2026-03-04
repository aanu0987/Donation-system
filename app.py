from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
from config import Config

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

# MongoDB Connection
client = MongoClient(app.config['MONGO_URI'])
db = client[app.config['MONGO_DB']]

# Collections
users = db.users
blood_donors = db.blood_donors
organ_donors = db.organ_donors
recipients = db.recipients
hospitals = db.hospitals
donations = db.donations
notifications = db.notifications
emergency_requests = db.emergency_requests
matches = db.matches

# Helper Functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'danger')
            return redirect(url_for('login'))
        
        user = users.find_one({'_id': ObjectId(session['user_id'])})
        if not user or user.get('user_type') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        user = users.find_one({'_id': ObjectId(session['user_id'])})
        if user:
            user['_id'] = str(user['_id'])
        return user
    return None

# Routes
@app.route('/')
def index():
    user = get_current_user()
    return render_template('index.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')

        # Check if user exists
        if users.find_one({'username': username}):
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if users.find_one({'email': email}):
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        # Create new user
        hashed_password = generate_password_hash(password)
        user_data = {
            'username': username,
            'email': email,
            'password_hash': hashed_password,
            'user_type': user_type,
            'full_name': full_name,
            'phone': phone,
            'address': address,
            'city': city,
            'is_verified': False if user_type != 'admin' else True,
            'created_at': datetime.utcnow()
        }
        
        result = users.insert_one(user_data)
        user_id = result.inserted_id

        # Create specific profile based on user type
        if user_type == 'donor':
            blood_donor_data = {
                'user_id': user_id,
                'blood_group': request.form.get('blood_group', ''),
                'last_donation_date': None,
                'is_eligible': True,
                'medical_conditions': request.form.get('medical_conditions', ''),
                'total_donations': 0,
                'created_at': datetime.utcnow()
            }
            blood_donors.insert_one(blood_donor_data)
            
            if request.form.get('is_organ_donor'):
                organs = request.form.getlist('organs')
                organ_donor_data = {
                    'user_id': user_id,
                    'kidney': 'kidney' in organs,
                    'liver': 'liver' in organs,
                    'heart': 'heart' in organs,
                    'lungs': 'lungs' in organs,
                    'cornea': 'cornea' in organs,
                    'medical_history': request.form.get('medical_history', ''),
                    'consent_verified': False,
                    'created_at': datetime.utcnow()
                }
                organ_donors.insert_one(organ_donor_data)
        
        elif user_type == 'recipient':
            recipient_data = {
                'user_id': user_id,
                'required_blood_group': request.form.get('required_blood_group', ''),
                'required_organ': request.form.get('required_organ', ''),
                'urgency_level': request.form.get('urgency_level', 'Medium'),
                'medical_reports': request.form.get('medical_reports', ''),
                'status': 'Pending',
                'request_date': datetime.utcnow(),
                'created_at': datetime.utcnow()
            }
            recipients.insert_one(recipient_data)
        
        elif user_type == 'hospital':
            hospital_data = {
                'user_id': user_id,
                'hospital_name': full_name,
                'license_number': request.form.get('license_number', ''),
                'verified': False,
                'created_at': datetime.utcnow()
            }
            hospitals.insert_one(hospital_data)
        
        # Create welcome notification
        notification_data = {
            'user_id': user_id,
            'message': f'Welcome to LifeLink, {full_name}!',
            'type': 'welcome',
            'is_read': False,
            'created_at': datetime.utcnow()
        }
        notifications.insert_one(notification_data)
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    user = get_current_user()
    return render_template('register.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = users.find_one({'username': username})
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            session['user_id'] = str(user_data['_id'])
            session.permanent = True
            
            # Create welcome back notification
            notification_data = {
                'user_id': user_data['_id'],
                'message': f'Welcome back, {user_data["full_name"]}!',
                'type': 'welcome',
                'is_read': False,
                'created_at': datetime.utcnow()
            }
            notifications.insert_one(notification_data)
            
            flash('Login successful!', 'success')
            
            # Redirect based on user type
            if user_data['user_type'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user_data['user_type'] == 'hospital':
                return redirect(url_for('hospital_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    user = get_current_user()
    return render_template('login.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    
    if user['user_type'] == 'donor':
        blood_donor = blood_donors.find_one({'user_id': ObjectId(user['_id'])})
        organ_donor = organ_donors.find_one({'user_id': ObjectId(user['_id'])})
        donor_donations = list(donations.find({'donor_id': ObjectId(user['_id'])}))
        donor_notifications = list(notifications.find({
            'user_id': ObjectId(user['_id']),
            'is_read': False
        }).sort('created_at', -1))
        
        # Convert ObjectId to string for JSON serialization
        for donation in donor_donations:
            donation['_id'] = str(donation['_id'])
            donation['donor_id'] = str(donation['donor_id'])
        
        for notification in donor_notifications:
            notification['_id'] = str(notification['_id'])
            notification['user_id'] = str(notification['user_id'])
        
        return render_template('donor.html', 
                             user=user,
                             donor=blood_donor, 
                             organ_donor=organ_donor, 
                             donations=donor_donations, 
                             notifications=donor_notifications)
    
    elif user['user_type'] == 'recipient':
        recipient = recipients.find_one({'user_id': ObjectId(user['_id'])})
        recipient_matches = list(matches.find({'recipient_id': ObjectId(user['_id'])}))
        
        if recipient:
            recipient['_id'] = str(recipient['_id'])
            recipient['user_id'] = str(recipient['user_id'])
        
        for match in recipient_matches:
            match['_id'] = str(match['_id'])
            match['recipient_id'] = str(match['recipient_id'])
        
        return render_template('recipient.html', user=user, recipient=recipient, matches=recipient_matches)
    
    return render_template('dashboard.html', user=user)

@app.route('/hospital/dashboard')
@login_required
def hospital_dashboard():
    user = get_current_user()
    
    if user['user_type'] != 'hospital':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    hospital = hospitals.find_one({'user_id': ObjectId(user['_id'])})
    
    if hospital:
        hospital['_id'] = str(hospital['_id'])
        hospital['user_id'] = str(hospital['user_id'])
    
    # Get all donors with their user info
    donor_list = []
    donor_cursor = blood_donors.aggregate([
        {
            '$lookup': {
                'from': 'users',
                'localField': 'user_id',
                'foreignField': '_id',
                'as': 'user'
            }
        },
        {'$unwind': '$user'}
    ])
    
    for donor in donor_cursor:
        donor['_id'] = str(donor['_id'])
        donor['user_id'] = str(donor['user_id'])
        donor['user']['_id'] = str(donor['user']['_id'])
        donor_list.append(donor)
    
    recipient_list = []
    recipient_cursor = recipients.find()
    for recipient in recipient_cursor:
        recipient['_id'] = str(recipient['_id'])
        recipient['user_id'] = str(recipient['user_id'])
        recipient_list.append(recipient)
    
    request_list = []
    request_cursor = donations.find({'hospital_id': ObjectId(user['_id'])})
    for donation_req in request_cursor:
        donation_req['_id'] = str(donation_req['_id'])
        if 'donor_id' in donation_req:
            donation_req['donor_id'] = str(donation_req['donor_id'])
        if 'recipient_id' in donation_req and donation_req['recipient_id']:
            donation_req['recipient_id'] = str(donation_req['recipient_id'])
        if 'hospital_id' in donation_req:
            donation_req['hospital_id'] = str(donation_req['hospital_id'])
        request_list.append(donation_req)
    
    return render_template('hospital.html', 
                         user=user,
                         hospital=hospital, 
                         requests=request_list,
                         donors=donor_list, 
                         recipients=recipient_list)

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    user = get_current_user()
    
    # Get statistics
    stats = {
        'total_users': users.count_documents({}),
        'blood_donors': blood_donors.count_documents({}),
        'organ_donors': organ_donors.count_documents({}),
        'recipients': recipients.count_documents({}),
        'hospitals': users.count_documents({'user_type': 'hospital'}),
        'donations': donations.count_documents({})
    }
    
    user_list = []
    user_cursor = users.find()
    for db_user in user_cursor:
        db_user['_id'] = str(db_user['_id'])
        user_list.append(db_user)
    
    # Get pending hospitals
    pending_hospitals = []
    hospital_cursor = hospitals.aggregate([
        {
            '$match': {'verified': False}
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'user_id',
                'foreignField': '_id',
                'as': 'user'
            }
        },
        {'$unwind': '$user'}
    ])
    
    for hospital in hospital_cursor:
        hospital['_id'] = str(hospital['_id'])
        hospital['user_id'] = str(hospital['user_id'])
        hospital['email'] = hospital['user']['email']
        hospital['phone'] = hospital['user']['phone']
        hospital['created_at'] = hospital['user']['created_at']
        pending_hospitals.append(hospital)
    
    return render_template('admin.html', user=user, users=user_list, stats=stats, pending_hospitals=pending_hospitals)

@app.route('/search-donors', methods=['POST'])
@login_required
def search_donors():
    data = request.json
    blood_group = data.get('blood_group')
    organ_type = data.get('organ_type')
    city = data.get('city')
    
    results = []
    
    # Search blood donors
    if blood_group:
        blood_donor_cursor = blood_donors.aggregate([
            {
                '$match': {
                    'blood_group': blood_group,
                    'is_eligible': True
                }
            },
            {
                '$lookup': {
                    'from': 'users',
                    'localField': 'user_id',
                    'foreignField': '_id',
                    'as': 'user'
                }
            },
            {'$unwind': '$user'}
        ])
        
        for donor in blood_donor_cursor:
            if not city or donor['user']['city'].lower() == city.lower():
                results.append({
                    'id': str(donor['user']['_id']),
                    'name': donor['user']['full_name'],
                    'blood_group': donor['blood_group'],
                    'last_donation': donor.get('last_donation_date', 'Never'),
                    'city': donor['user']['city'],
                    'type': 'blood'
                })
    
    # Search organ donors
    if organ_type:
        organ_query = {organ_type: True, 'consent_verified': True}
        organ_donor_cursor = organ_donors.aggregate([
            {
                '$match': organ_query
            },
            {
                '$lookup': {
                    'from': 'users',
                    'localField': 'user_id',
                    'foreignField': '_id',
                    'as': 'user'
                }
            },
            {'$unwind': '$user'}
        ])
        
        for donor in organ_donor_cursor:
            if not city or donor['user']['city'].lower() == city.lower():
                results.append({
                    'id': str(donor['user']['_id']),
                    'name': donor['user']['full_name'],
                    'organ': organ_type,
                    'city': donor['user']['city'],
                    'type': 'organ'
                })
    
    return jsonify(results)

@app.route('/request-donation', methods=['POST'])
@login_required
def request_donation():
    data = request.json
    donation_type = data.get('type')
    donor_id = ObjectId(data.get('donor_id'))
    user = get_current_user()
    
    if user['user_type'] == 'recipient':
        recipient_id = ObjectId(user['_id'])
        hospital_id = None
    elif user['user_type'] == 'hospital':
        recipient_id = ObjectId(data.get('recipient_id')) if data.get('recipient_id') else None
        hospital_id = ObjectId(user['_id'])
    else:
        return jsonify({'success': False, 'message': 'Invalid user type'})
    
    donation_data = {
        'donor_id': donor_id,
        'recipient_id': recipient_id,
        'hospital_id': hospital_id,
        'donation_type': donation_type,
        'blood_group': data.get('blood_group'),
        'organ_type': data.get('organ_type'),
        'donation_date': datetime.utcnow(),
        'status': 'Pending'
    }
    
    result = donations.insert_one(donation_data)
    
    # Notify donor
    notification_data = {
        'user_id': donor_id,
        'message': f'New donation request received. Please check your dashboard.',
        'type': 'donation_request',
        'is_read': False,
        'created_at': datetime.utcnow()
    }
    notifications.insert_one(notification_data)
    
    return jsonify({'success': True, 'message': 'Donation request sent successfully', 'id': str(result.inserted_id)})

@app.route('/notifications')
@login_required
def get_notifications():
    user = get_current_user()
    notification_list = list(notifications.find({
        'user_id': ObjectId(user['_id']),
        'is_read': False
    }).sort('created_at', -1))
    
    result = []
    for n in notification_list:
        result.append({
            'id': str(n['_id']),
            'message': n['message'],
            'type': n['type'],
            'created_at': n['created_at'].strftime('%Y-%m-%d %H:%M') if n['created_at'] else ''
        })
    
    return jsonify(result)

@app.route('/notifications/read/<notification_id>')
@login_required
def mark_notification_read(notification_id):
    user = get_current_user()
    notifications.update_one(
        {'_id': ObjectId(notification_id), 'user_id': ObjectId(user['_id'])},
        {'$set': {'is_read': True}}
    )
    return jsonify({'success': True})

@app.route('/api/emergency-requests')
def get_emergency_requests():
    city = request.args.get('city')
    query = {'status': 'Active'}
    if city:
        query['city'] = city
    
    emergency_list = list(emergency_requests.find(query).sort('created_at', -1).limit(5))
    
    result = []
    for e in emergency_list:
        result.append({
            'id': str(e['_id']),
            'hospital': e.get('hospital_name', 'Unknown'),
            'blood_group': e.get('blood_group'),
            'organ_type': e.get('organ_type'),
            'reason': e.get('urgency_reason', ''),
            'created_at': e['created_at'].strftime('%Y-%m-%d %H:%M') if e['created_at'] else ''
        })
    
    return jsonify(result)

@app.route('/api/user/<user_id>')
@login_required
@admin_required
def get_user(user_id):
    user_data = users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        user_data['_id'] = str(user_data['_id'])
        user_data.pop('password_hash', None)
        return jsonify(user_data)
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/verify-user/<user_id>', methods=['POST'])
@login_required
@admin_required
def verify_user(user_id):
    users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'is_verified': True}}
    )
    return jsonify({'success': True})

@app.route('/api/delete-user/<user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    # Delete user and related records
    user_obj_id = ObjectId(user_id)
    users.delete_one({'_id': user_obj_id})
    blood_donors.delete_one({'user_id': user_obj_id})
    organ_donors.delete_one({'user_id': user_obj_id})
    recipients.delete_one({'user_id': user_obj_id})
    hospitals.delete_one({'user_id': user_obj_id})
    notifications.delete_many({'user_id': user_obj_id})
    
    return jsonify({'success': True})

@app.route('/api/verify-hospital/<hospital_id>', methods=['POST'])
@login_required
@admin_required
def verify_hospital(hospital_id):
    hospitals.update_one(
        {'_id': ObjectId(hospital_id)},
        {'$set': {'verified': True}}
    )
    
    # Also verify the user
    hospital = hospitals.find_one({'_id': ObjectId(hospital_id)})
    if hospital:
        users.update_one(
            {'_id': hospital['user_id']},
            {'$set': {'is_verified': True}}
        )
    
    return jsonify({'success': True})

@app.route('/api/reject-hospital/<hospital_id>', methods=['POST'])
@login_required
@admin_required
def reject_hospital(hospital_id):
    hospitals.delete_one({'_id': ObjectId(hospital_id)})
    return jsonify({'success': True})

@app.route('/api/add-user', methods=['POST'])
@login_required
@admin_required
def add_user():
    data = request.json
    
    # Check if user exists
    if users.find_one({'username': data['username']}):
        return jsonify({'success': False, 'message': 'Username already exists'})
    
    if users.find_one({'email': data['email']}):
        return jsonify({'success': False, 'message': 'Email already registered'})
    
    # Create new user
    hashed_password = generate_password_hash(data['password'])
    user_data = {
        'username': data['username'],
        'email': data['email'],
        'password_hash': hashed_password,
        'user_type': data['user_type'],
        'full_name': data['full_name'],
        'phone': data['phone'],
        'city': data['city'],
        'address': data.get('address', ''),
        'is_verified': True,
        'created_at': datetime.utcnow()
    }
    
    result = users.insert_one(user_data)
    
    return jsonify({'success': True, 'id': str(result.inserted_id)})

# Create indexes and admin user
def init_db():
    # Create indexes
    users.create_index('username', unique=True)
    users.create_index('email', unique=True)
    users.create_index('user_type')
    
    blood_donors.create_index('user_id')
    blood_donors.create_index('blood_group')
    
    organ_donors.create_index('user_id')
    
    recipients.create_index('user_id')
    recipients.create_index('urgency_level')
    
    notifications.create_index('user_id')
    notifications.create_index('is_read')
    
    # Create admin user if not exists
    admin = users.find_one({'user_type': 'admin'})
    if not admin:
        admin_data = {
            'username': 'admin',
            'email': 'admin@lifelink.org',
            'password_hash': generate_password_hash('admin123'),
            'user_type': 'admin',
            'full_name': 'System Administrator',
            'is_verified': True,
            'created_at': datetime.utcnow()
        }
        users.insert_one(admin_data)
        print('Admin user created - Username: admin, Password: admin123')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)