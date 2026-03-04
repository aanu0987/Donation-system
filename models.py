# Helper functions for database operations

def serialize_notification(notification):
    """Convert notification to JSON-serializable dict"""
    return {
        'id': str(notification['_id']),
        'message': notification['message'],
        'type': notification['type'],
        'is_read': notification['is_read'],
        'created_at': notification['created_at'].isoformat() if notification.get('created_at') else None
    }

def serialize_donation_record(record):
    """Convert donation record to JSON-serializable dict"""
    return {
        'id': str(record['_id']),
        'donation_type': record.get('donation_type'),
        'blood_group': record.get('blood_group'),
        'organ_type': record.get('organ_type'),
        'donation_date': record['donation_date'].isoformat() if record.get('donation_date') else None,
        'status': record.get('status')
    }

def get_eligible_blood_donors(db, blood_group, city=None):
    """Get eligible blood donors by blood group and city"""
    from bson.objectid import ObjectId
    
    query = {
        'blood_group': blood_group,
        'is_eligible': True
    }
    
    donors = []
    blood_donor_cursor = db.blood_donors.find(query)
    
    for donor in blood_donor_cursor:
        user = db.users.find_one({'_id': donor['user_id']})
        if user and user.get('is_verified'):
            if not city or user.get('city', '').lower() == city.lower():
                donor['user'] = user
                donors.append(donor)
    
    return donors

def get_eligible_organ_donors(db, organ_type, city=None):
    """Get eligible organ donors by organ type and city"""
    organ_query = {organ_type: True, 'consent_verified': True}
    
    donors = []
    organ_donor_cursor = db.organ_donors.find(organ_query)
    
    for donor in organ_donor_cursor:
        user = db.users.find_one({'_id': donor['user_id']})
        if user and user.get('is_verified'):
            if not city or user.get('city', '').lower() == city.lower():
                donor['user'] = user
                donors.append(donor)
    
    return donors

def get_urgent_requests(db, urgency_level='High'):
    """Get urgent recipient requests"""
    from bson.objectid import ObjectId
    
    query = {
        'urgency_level': {'$in': ['High', 'Emergency']},
        'status': 'Pending'
    }
    
    recipients = []
    recipient_cursor = db.recipients.find(query)
    
    for recipient in recipient_cursor:
        user = db.users.find_one({'_id': recipient['user_id']})
        if user:
            recipient['user'] = user
            recipients.append(recipient)
    
    return recipients

def find_matches(db, recipient_id):
    """Find matching donors for a recipient"""
    from bson.objectid import ObjectId
    
    recipient = db.recipients.find_one({'_id': ObjectId(recipient_id)})
    if not recipient:
        return []
    
    matches = []
    
    # Blood match
    if recipient.get('required_blood_group'):
        blood_donors = get_eligible_blood_donors(db, recipient['required_blood_group'])
        for donor in blood_donors:
            matches.append({
                'donor_id': donor['user_id'],
                'donor_name': donor['user']['full_name'],
                'donor_city': donor['user']['city'],
                'blood_group': donor['blood_group'],
                'match_score': 90,  # Calculate based on various factors
                'type': 'blood'
            })
    
    # Organ match
    if recipient.get('required_organ'):
        organ_donors = get_eligible_organ_donors(db, recipient['required_organ'])
        for donor in organ_donors:
            matches.append({
                'donor_id': donor['user_id'],
                'donor_name': donor['user']['full_name'],
                'donor_city': donor['user']['city'],
                'organ_type': recipient['required_organ'],
                'match_score': 85,  # Calculate based on various factors
                'type': 'organ'
            })
    
    # Remove duplicates based on donor_id
    unique_matches = []
    seen_donors = set()
    
    for match in matches:
        if match['donor_id'] not in seen_donors:
            seen_donors.add(match['donor_id'])
            unique_matches.append(match)
    
    return unique_matches