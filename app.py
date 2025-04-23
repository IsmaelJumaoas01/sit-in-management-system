from flask import Flask
import os

app = Flask(__name__)

# Use a strong secret key from environment variable or generate a random one
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Configure session to be more secure
app.config.update(
    SESSION_COOKIE_SECURE=True,  # Only send cookie over HTTPS
    SESSION_COOKIE_HTTPONLY=True,  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE='Lax',  # Protect against CSRF
    PERMANENT_SESSION_LIFETIME=1800  # 30 minutes session lifetime
)

# Import routes
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.lab_routes import lab_bp
from routes.admin_routes import admin_bp
from routes.staff_routes import staff_bp
from routes.announcement_routes import announcement_bp
from routes.lab_resources import lab_resources
from routes.rewards_routes import rewards_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(lab_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(staff_bp, url_prefix='/staff')
app.register_blueprint(announcement_bp)
app.register_blueprint(lab_resources)
app.register_blueprint(rewards_bp)

if __name__ == '__main__':
    # For development only - in production, use proper HTTPS
    app.config['SESSION_COOKIE_SECURE'] = False
    app.run(debug=True)  
