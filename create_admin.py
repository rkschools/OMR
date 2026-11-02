import firebase_admin
from firebase_admin import auth, firestore

try:
    firebase_admin.initialize_app(options={'projectId': 'rise-omr-backend-2027'})
except:
    pass

email = 'admin@rise.com'
password = 'password123'

try:
    user = auth.create_user(email=email, password=password)
    print(f"Created new user: {user.uid}")
except auth.EmailAlreadyExistsError:
    user = auth.get_user_by_email(email)
    auth.update_user(user.uid, password=password)
    print(f"Updated existing user: {user.uid}")

db = firestore.client()
db.collection('users').document(user.uid).set({
    'email': email,
    'role': 'admin'
})

db.collection('system').document('setup').set({
    'isSetup': True
})
print("Done! You can now log in.")
