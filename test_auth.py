import firebase_admin
from firebase_admin import auth

try:
    firebase_admin.initialize_app(options={'projectId': 'rise-omr-backend-2027'})
    print("App initialized successfully without credentials!")
    # Just creating the app without credentials works if we only use verify_id_token.
except Exception as e:
    print("Init failed:", e)
