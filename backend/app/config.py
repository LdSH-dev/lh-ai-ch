import os


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/tmp/docproc_uploads")
    
    # CORS Configuration - comma-separated list of allowed origins
    # Example: "http://localhost:5173,https://app.example.com"
    CORS_ORIGINS: list[str] = []

    def __init__(self):
        self._parse_cors_origins()
        self._validate_required_vars()

    def _parse_cors_origins(self):
        """Parse CORS_ORIGINS from environment variable."""
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            self.CORS_ORIGINS = [
                origin.strip() 
                for origin in cors_env.split(",") 
                if origin.strip()
            ]

    def _validate_required_vars(self):
        missing = []
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")
        if not self.SECRET_KEY:
            missing.append("SECRET_KEY")
        if not self.CORS_ORIGINS:
            missing.append("CORS_ORIGINS")
        
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Please set them before starting the application."
            )


settings = Settings()
