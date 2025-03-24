from flask import Flask

app = Flask(__name__)
app.secret_key = 'xdsxdxdxdasxdsxsaasaxasdaxda'

# Import routes
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.lab_routes import lab_bp
from routes.admin_routes import admin_bp
from routes.staff_routes import staff_bp
from routes.announcement_routes import announcement_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(lab_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(staff_bp, url_prefix='/staff')
app.register_blueprint(announcement_bp)

if __name__ == '__main__':
    # Make the app accessible on LAN
    app.run(debug=True, host='172.19.131.151', port='5000')  # Use a port of your choice
