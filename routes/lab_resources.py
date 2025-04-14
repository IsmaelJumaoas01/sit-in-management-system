from flask import Blueprint, request, jsonify, send_file, current_app, session
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from db import get_db_connection
import mimetypes
from functools import wraps

lab_resources = Blueprint('lab_resources', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip', 'rar'}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'IDNO' not in session:
            return jsonify({'error': 'Please log in first'}), 401
        
        # Add user info to request object
        request.user_id = session.get('IDNO')
        request.user_course = session.get('COURSE')
        
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'IDNO' not in session or session.get('USER_TYPE') != 'STAFF':
            return jsonify({'error': 'Staff access required'}), 403
            
        # Add staff info to request object
        request.staff_id = session.get('IDNO')
        
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@lab_resources.route('/api/courses', methods=['GET'])
@login_required
def get_courses():
    print("\n=== Starting get_courses endpoint ===")
    db = None
    cursor = None
    try:
        print("Getting database connection...")
        db = get_db_connection()
        if not db:
            print("Error: Could not establish database connection")
            return jsonify({'error': 'Database connection failed'}), 500
            
        print("Creating cursor...")
        cursor = db.cursor(dictionary=True)
        
        # Get unique courses from USERS table
        query = """
            SELECT DISTINCT COURSE 
            FROM USERS 
            WHERE COURSE IS NOT NULL AND COURSE != ''
            ORDER BY COURSE
        """
        print(f"Executing query: {query}")
        cursor.execute(query)
        
        courses = cursor.fetchall()
        print(f"Raw courses data: {courses}")
        
        if not courses:
            print("No courses found in database")
            return jsonify([]), 200
        
        # Extract just the course names
        course_list = [course['COURSE'] for course in courses]
        print(f"Processed course list: {course_list}")
        
        return jsonify(course_list), 200
        
    except Exception as e:
        print(f"Error in get_courses: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500
    finally:
        print("Cleaning up database connections...")
        if cursor:
            try:
                cursor.close()
                print("Cursor closed successfully")
            except Exception as e:
                print(f"Error closing cursor: {e}")
        if db:
            try:
                db.close()
                print("Database connection closed successfully")
            except Exception as e:
                print(f"Error closing database connection: {e}")
        print("=== Finished get_courses endpoint ===\n")

@lab_resources.route('/api/resources', methods=['POST'])
@login_required
def create_resource():
    print("\n=== Starting create_resource endpoint ===")
    print("Session data:", dict(session))  # Log all session data
    
    db = None
    cursor = None
    try:
        # Check if user is staff
        user_type = session.get('USER_TYPE')  # Changed from ROLE to USER_TYPE
        print(f"User type from session: {user_type}")
        
        if user_type != 'STAFF':
            print(f"Error: User is not staff. User type: {user_type}")
            return jsonify({'error': 'Staff access required'}), 403

        print("Staff authentication successful")
        db = get_db_connection()
        if not db:
            print("Error: Could not establish database connection")
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = db.cursor(dictionary=True)
        
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        resource_type = request.form.get('resource_type')
        courses = request.form.getlist('courses[]')
        
        print(f"Received data - Title: {title}, Type: {resource_type}, Courses: {courses}")
        
        if not all([title, description, resource_type, courses]):
            print("Error: Missing required fields")
            return jsonify({'error': 'Missing required fields'}), 400
            
        content_url = None
        content_text = None
        
        if resource_type == 'FILE':
            print("Processing FILE type resource")
            if 'file' not in request.files:
                print("Error: No file uploaded")
                return jsonify({'error': 'No file uploaded'}), 400
                
            file = request.files['file']
            if file.filename == '':
                print("Error: No file selected")
                return jsonify({'error': 'No file selected'}), 400
                
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                content_url = filename
                print(f"File saved as: {filename}")
                
        elif resource_type == 'LINK':
            print("Processing LINK type resource")
            content_url = request.form.get('content_url')
            if not content_url:
                print("Error: URL is required for link type resources")
                return jsonify({'error': 'URL is required for link type resources'}), 400
                
        elif resource_type == 'TEXT':
            print("Processing TEXT type resource")
            content_text = request.form.get('content_text')
            if not content_text:
                print("Error: Text content is required for text type resources")
                return jsonify({'error': 'Text content is required for text type resources'}), 400
        
        # Validate courses
        print("Validating courses:", courses)
        if not courses:
            print("Error: No courses selected")
            return jsonify({'error': 'Please select at least one course'}), 400

        # Create placeholders for SQL query
        placeholders = ','.join(['%s'] * len(courses))
        query = f"""
            SELECT DISTINCT COURSE 
            FROM USERS 
            WHERE COURSE IN ({placeholders})
        """
        print(f"Executing query: {query} with params: {courses}")
        cursor.execute(query, courses)
        
        valid_courses = cursor.fetchall()
        print("Valid courses found:", valid_courses)
        
        if len(valid_courses) != len(courses):
            print("Error: Invalid courses detected")
            return jsonify({'error': 'One or more invalid courses selected'}), 400
        
        # Insert resource with is_enabled set to TRUE by default
        print("Inserting resource into database")
        cursor.execute("""
            INSERT INTO lab_resources 
            (title, description, resource_type, content_url, content_text, created_by, is_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
        """, (title, description, resource_type, content_url, content_text, session['IDNO']))
        
        resource_id = cursor.lastrowid
        print(f"Resource created with ID: {resource_id}")
        
        # Insert course mappings using the actual course names
        print("Creating course mappings")
        for course in courses:
            cursor.execute("""
                INSERT INTO resource_course_mapping (resource_id, course_id)
                VALUES (%s, %s)
            """, (resource_id, course))
            
        db.commit()
        print("=== Resource creation successful ===\n")
        return jsonify({'message': 'Resource created successfully', 'resource_id': resource_id}), 201
        
    except Exception as e:
        print(f"Error in create_resource: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        if db:
            db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        print("Cleaning up database connections...")
        if cursor:
            try:
                cursor.close()
                print("Cursor closed successfully")
            except Exception as e:
                print(f"Error closing cursor: {e}")
        if db:
            try:
                db.close()
                print("Database connection closed successfully")
            except Exception as e:
                print(f"Error closing database connection: {e}")
        print("=== Finished create_resource endpoint ===\n")

@lab_resources.route('/api/resources', methods=['GET'])
@login_required
def get_resources():
    try:
        print("\n=== Starting get_resources endpoint ===")
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        
        is_staff = hasattr(request, 'staff_id')
        print(f"User is staff: {is_staff}")
        print(f"User course: {request.user_course}")
        
        if is_staff:
            print("Fetching all resources for staff")
            # Staff can see all resources
            cursor.execute("""
                SELECT r.*, GROUP_CONCAT(rcm.course_id) as courses
                FROM lab_resources r
                LEFT JOIN resource_course_mapping rcm ON r.resource_id = rcm.resource_id
                GROUP BY r.resource_id, r.title, r.description, r.resource_type, 
                         r.content_url, r.content_text, r.created_by, r.created_at, 
                         r.is_enabled
                ORDER BY r.created_at DESC
            """)
        else:
            print("Fetching resources for student")
            # Students can only see enabled resources for their course
            cursor.execute("""
                SELECT DISTINCT r.*, GROUP_CONCAT(rcm.course_id) as courses
                FROM lab_resources r
                JOIN resource_course_mapping rcm ON r.resource_id = rcm.resource_id
                WHERE (r.is_enabled IS NULL OR r.is_enabled = TRUE)
                AND rcm.course_id = %s
                GROUP BY r.resource_id, r.title, r.description, r.resource_type, 
                         r.content_url, r.content_text, r.created_by, r.created_at, 
                         r.is_enabled
                ORDER BY r.created_at DESC
            """, (request.user_course,))
            
        resources = cursor.fetchall()
        print(f"Found {len(resources)} resources")
        
        # Convert resources to list of dicts and handle any NULL values
        formatted_resources = []
        for resource in resources:
            resource_dict = dict(resource)
            # Convert any None values to appropriate defaults
            resource_dict['is_enabled'] = True if resource_dict.get('is_enabled') is None else resource_dict['is_enabled']
            resource_dict['courses'] = resource_dict.get('courses', '').split(',') if resource_dict.get('courses') else []
            formatted_resources.append(resource_dict)
            
        print("=== Finished get_resources endpoint ===\n")
        return jsonify(formatted_resources), 200
        
    except Exception as e:
        print(f"Error in get_resources: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@lab_resources.route('/api/resources/<int:resource_id>', methods=['PUT'])
@staff_required
def update_resource(resource_id):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        
        title = request.form.get('title')
        description = request.form.get('description')
        is_enabled = request.form.get('is_enabled')
        courses = request.form.getlist('courses[]')
        
        update_query = "UPDATE lab_resources SET "
        update_params = []
        
        if title:
            update_query += "title = %s, "
            update_params.append(title)
        if description:
            update_query += "description = %s, "
            update_params.append(description)
        if is_enabled is not None:
            update_query += "is_enabled = %s, "
            update_params.append(is_enabled == 'true')
            
        update_query = update_query.rstrip(', ')
        update_query += " WHERE resource_id = %s"
        update_params.append(resource_id)
        
        cursor.execute(update_query, tuple(update_params))
        
        if courses:
            # Update course mappings
            cursor.execute("DELETE FROM resource_course_mapping WHERE resource_id = %s", (resource_id,))
            for course_id in courses:
                cursor.execute("""
                    INSERT INTO resource_course_mapping (resource_id, course_id)
                    VALUES (%s, %s)
                """, (resource_id, course_id))
                
        db.commit()
        return jsonify({'message': 'Resource updated successfully'}), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@lab_resources.route('/api/resources/<int:resource_id>', methods=['DELETE'])
@staff_required
def delete_resource(resource_id):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        
        # Get resource info before deletion
        cursor.execute("SELECT * FROM lab_resources WHERE resource_id = %s", (resource_id,))
        resource = cursor.fetchone()
        
        if not resource:
            return jsonify({'error': 'Resource not found'}), 404
            
        # Delete the file if it exists
        if resource['resource_type'] == 'FILE' and resource['content_url']:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], resource['content_url'])
            if os.path.exists(file_path):
                os.remove(file_path)
                
        # Delete from database (cascade will handle mappings)
        cursor.execute("DELETE FROM lab_resources WHERE resource_id = %s", (resource_id,))
        db.commit()
        
        return jsonify({'message': 'Resource deleted successfully'}), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@lab_resources.route('/api/resources/download/<int:resource_id>', methods=['GET'])
@login_required
def download_resource(resource_id):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT r.* FROM lab_resources r
            LEFT JOIN resource_course_mapping rcm ON r.resource_id = rcm.resource_id
            WHERE r.resource_id = %s
            AND (r.is_enabled = TRUE OR %s)
            AND (rcm.course_id = %s OR %s)
        """, (resource_id, hasattr(request, 'staff_id'), 
              getattr(request, 'user_course', None), hasattr(request, 'staff_id')))
        
        resource = cursor.fetchone()
        
        if not resource:
            return jsonify({'error': 'Resource not found or access denied'}), 404
            
        if resource['resource_type'] != 'FILE' or not resource['content_url']:
            return jsonify({'error': 'Resource is not a file'}), 400
            
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], resource['content_url'])
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
            
        # Log access
        cursor.execute("""
            INSERT INTO resource_access_logs (resource_id, user_id, user_type)
            VALUES (%s, %s, %s)
        """, (resource_id, 
              request.staff_id if hasattr(request, 'staff_id') else request.user_id,
              'STAFF' if hasattr(request, 'staff_id') else 'STUDENT'))
        db.commit()
        
        return send_file(file_path, 
                        as_attachment=True,
                        download_name=resource['content_url'].split('_', 2)[2])
                        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 