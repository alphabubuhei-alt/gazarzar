from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "GazarZar"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./gazarzar.db"

    SECRET_KEY: str = "changeme_replace_with_random_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    UPLOAD_DIR: str = "uploads"
    MAX_IMAGE_SIZE_MB: int = 10

    QPAY_BASE_URL: str = "https://merchant.qpay.mn/v2"
    QPAY_USERNAME: str = ""
    QPAY_PASSWORD: str = ""
    QPAY_INVOICE_CODE: str = ""

    SMS_API_URL: str = "https://rest.moceanapi.com/rest/2/sms"
    SMS_API_KEY: str = ""
    SMS_API_SECRET: str = ""
    SMS_SENDER: str = "GazarZar"
    FIREBASE_PROJECT_ID: str = "gazarzar-f79e1"

    SMS_PROVIDER: str = "twilio"  # "twilio", "callpro", "mock"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Cloudflare R2 - persistent image storage
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_PUBLIC_URL: str = ""

    class Config:
        env_file = ".env"

settings = Settings()

# Hotfix: Correct R2 Account ID typo ('b495...' -> 'b493...') configured in Render env vars
if settings.R2_ACCOUNT_ID:
    val = settings.R2_ACCOUNT_ID.strip()
    if val in ("b495cf2611719285a7d4e635b744d13d", "b495c26111719285a7d4a635b744d13d"):
        settings.R2_ACCOUNT_ID = "b493cf2611719285a7d4e635b744d13d"
