import firebase_admin
from firebase_admin import auth, credentials
from app.core.config import settings

# Initialize Firebase Admin SDK
# If it's already initialized, do not initialize it again.
if not firebase_admin._apps:
    try:
        # In modern environment, Firebase Admin can be initialized with project ID only.
        # This allows us to verify ID tokens without requiring a private service account key JSON file!
        firebase_admin.initialize_app(options={
            'projectId': settings.FIREBASE_PROJECT_ID
        })
        print(f"[Firebase] Initialized successfully for project: {settings.FIREBASE_PROJECT_ID}")
    except Exception as e:
        print(f"[Firebase Error] Failed to initialize Firebase Admin: {e}")

def verify_firebase_token(id_token: str) -> str:
    """
    Verifies the Firebase ID token and returns the verified phone number.
    Raises ValueError if token is invalid or expired.
    """
    try:
        # Verify the ID token using the admin SDK
        decoded_token = auth.verify_id_token(id_token)
        phone_number = decoded_token.get("phone_number")
        
        if not phone_number:
            raise ValueError("Firebase токенд утасны дугаар олдсонгүй")
            
        return phone_number
    except Exception as e:
        print(f"[Firebase Auth Verification Error] {e}")
        raise ValueError(f"Firebase токен хүчингүй байна: {str(e)}")
