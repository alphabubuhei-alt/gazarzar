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

    # Cloudflare Images - persistent image storage
    CF_ACCOUNT_ID: str = ""          # Cloudflare Account ID
    CF_IMAGES_API_TOKEN: str = ""    # API Token with Images:Edit permission
    CF_IMAGES_ACCOUNT_HASH: str = "" # Account hash shown in Images dashboard

    class Config:
        env_file = ".env"

settings = Settings()
