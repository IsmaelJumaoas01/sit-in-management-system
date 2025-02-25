from flask import Flask

app = Flask(__name__)
app.secret_key = 'xdsxdxdxdasxdsxsaasaxasdaxda'

# Import routes
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.lab_routes import lab_bp
from routes.admin_routes import admin_bp  # Import the admin blueprint

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(lab_bp)
app.register_blueprint(admin_bp)  # Register the admin blueprint

if __name__ == '__main__':
    app.run(debug=True)
