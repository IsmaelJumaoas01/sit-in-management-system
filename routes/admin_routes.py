from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from db import get_db_connection
import os
from werkzeug.utils import secure_filename
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# Add configuration for file uploads
UPLOAD_FOLDER = 'static/profile_pictures'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/admin_dashboard')
def admin_dashboard():
    if 'IDNO' in session and session['USER_TYPE'] == 'ADMIN':
        # Get announcements for admin dashboard
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT ANNOUNCEMENT_ID, TITLE, CONTENT, DATE_POSTED, POSTED_BY 
                FROM ANNOUNCEMENTS 
                ORDER BY DATE_POSTED DESC
            """)
            announcements = cursor.fetchall()
            announcements_list = []
            for ann in announcements:
                announcements_list.append({
                    'announcement_id': ann[0],
                    'title': ann[1],
                    'content': ann[2],
                    'date_posted': ann[3].strftime("%Y-%m-%d %H:%M:%S") if ann[3] else "",
                    'posted_by': ann[4]
                })
        except Exception as e:
            announcements_list = []
        finally:
            cursor.close()
            conn.close()

        return render_template('admin_dashboard.html',
                            admin_name=f"{session['FIRSTNAME']} {session['LASTNAME']}",
                            email=session['EMAIL'],
                            announcements=announcements_list)
    flash('You must be logged in as an admin to view this page.', 'error')
    return redirect(url_for('auth.login'))

@admin_bp.route('/add_subject', methods=['POST'])
def add_subject():
    data = request.get_json()
    subject_name = data.get('subjectName')
    description = data.get('description')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO SUBJECTS (SUBJECT_NAME, DESCRIPTION) VALUES (%s, %s)", (subject_name, description))
        conn.commit()
        return jsonify({'message': 'Subject added successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/schedule_subject', methods=['POST'])
def schedule_subject():
    data = request.get_json()
    subject_id = data.get('subject')
    lab_id = data.get('lab')
    instructor_id = data.get('instructor')
    day = data.get('day')
    start_time = data.get('startTime')
    end_time = data.get('endTime')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO SEMESTER_SCHEDULES (LAB_ID, SUBJECT_ID, INSTRUCTOR_IDNO, DAY, START_TIME, END_TIME)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (lab_id, subject_id, instructor_id, day, start_time, end_time))
        conn.commit()
        return jsonify({'message': 'Subject scheduled successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/get_subjects')
def get_subjects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUBJECT_ID, SUBJECT_NAME FROM SUBJECTS")
    subjects = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([{'SUBJECT_ID': subject[0], 'SUBJECT_NAME': subject[1]} for subject in subjects])

@admin_bp.route('/get_labs')
def get_labs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT LAB_ID, LAB_NAME FROM LABORATORIES")
    labs = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([{'LAB_ID': lab[0], 'LAB_NAME': lab[1]} for lab in labs])

@admin_bp.route('/get_schedule')
def get_schedule():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT S.DAY, S.START_TIME, S.END_TIME, SUB.SUBJECT_NAME, L.LAB_NAME
        FROM SEMESTER_SCHEDULES S
        JOIN SUBJECTS SUB ON S.SUBJECT_ID = SUB.SUBJECT_ID
        JOIN LABORATORIES L ON S.LAB_ID = L.LAB_ID
    """)
    schedule = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([{'DAY': entry[0], 'START_TIME': entry[1], 'END_TIME': entry[2], 'SUBJECT_NAME': entry[3], 'LAB_NAME': entry[4]} for entry in schedule])

@admin_bp.route('/update_profile_picture', methods=['POST'])
def update_profile_picture():
    if 'IDNO' not in session or session.get('USER_TYPE') != 'ADMIN':
        return jsonify({'error': 'Unauthorized'}), 401

    if 'profile_picture' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        # Create upload folder if it doesn't exist
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # Secure the filename and create unique filename
        filename = secure_filename(file.filename)
        user_id = session['IDNO']
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"profile_{user_id}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, new_filename)
        
        # Save the file
        file.save(filepath)

        # Update the user's profile picture URL in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE USERS SET PROFILE_PICTURE_URL = %s WHERE IDNO = %s",
                (f"/static/profile_pictures/{new_filename}", user_id)
            )
            conn.commit()
            
            # Update session with new profile picture URL
            session['PROFILE_PICTURE_URL'] = f"/static/profile_pictures/{new_filename}"
            
            return jsonify({
                'success': True,
                'profile_picture_url': f"/static/profile_pictures/{new_filename}"
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    return jsonify({'error': 'Invalid file type'}), 400

@admin_bp.route('/edit_info', methods=['GET', 'POST'])
def edit_info():
    if 'IDNO' not in session or session['USER_TYPE'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'POST':
        new_firstname = request.form['firstname']
        new_lastname = request.form['lastname']
        new_email = request.form['email']
        new_password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if new_password:
                # Update with new password
                cursor.execute("""
                    UPDATE USERS 
                    SET FIRSTNAME = %s, LASTNAME = %s, EMAIL = %s, PASSWORD = %s 
                    WHERE IDNO = %s
                """, (new_firstname, new_lastname, new_email, new_password, session['IDNO']))
            else:
                # Update without changing password
                cursor.execute("""
                    UPDATE USERS 
                    SET FIRSTNAME = %s, LASTNAME = %s, EMAIL = %s 
                    WHERE IDNO = %s
                """, (new_firstname, new_lastname, new_email, session['IDNO']))

            conn.commit()
            
            # Update session data
            session['FIRSTNAME'] = new_firstname
            session['LASTNAME'] = new_lastname
            session['EMAIL'] = new_email

            return jsonify({
                'success': True,
                'message': 'Your details have been updated successfully!'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        finally:
            cursor.close()
            conn.close()

    return jsonify({'error': 'Invalid request method'}), 400

@admin_bp.route('/announcements', methods=['GET', 'POST'])
def manage_announcements():
    if 'IDNO' not in session or session['USER_TYPE'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        posted_by = session['IDNO']

        try:
            cursor.execute(
                "INSERT INTO ANNOUNCEMENTS (TITLE, CONTENT, POSTED_BY, DATE_POSTED) VALUES (%s, %s, %s, %s)",
                (title, content, posted_by, datetime.now())
            )
            conn.commit()
            return jsonify({'success': True, 'message': 'Announcement posted successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    elif request.method == 'GET':
        try:
            cursor.execute("""
                SELECT ANNOUNCEMENT_ID, TITLE, CONTENT, DATE_POSTED, POSTED_BY 
                FROM ANNOUNCEMENTS 
                ORDER BY DATE_POSTED DESC
            """)
            announcements = cursor.fetchall()
            result = []
            for ann in announcements:
                result.append({
                    'announcement_id': ann[0],
                    'title': ann[1],
                    'content': ann[2],
                    'date_posted': ann[3].strftime("%Y-%m-%d %H:%M:%S") if ann[3] else "",
                    'posted_by': ann[4]
                })
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

@admin_bp.route('/announcements/<int:announcement_id>', methods=['PUT', 'DELETE'])
def manage_announcement(announcement_id):
    if 'IDNO' not in session or session['USER_TYPE'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'PUT':
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')

        if not title or not content:
            return jsonify({'error': 'Title and content are required'}), 400

        try:
            cursor.execute("""
                UPDATE ANNOUNCEMENTS 
                SET TITLE = %s, CONTENT = %s 
                WHERE ANNOUNCEMENT_ID = %s
            """, (title, content, announcement_id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Announcement updated successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    elif request.method == 'DELETE':
        try:
            cursor.execute("DELETE FROM ANNOUNCEMENTS WHERE ANNOUNCEMENT_ID = %s", (announcement_id,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Announcement deleted successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

@admin_bp.route('/purposes', methods=['GET', 'POST'])
def manage_purposes():
    if 'IDNO' not in session or session['USER_TYPE'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.get_json()
        purpose_name = data.get('purposeName')

        if not purpose_name:
            return jsonify({'error': 'Purpose name is required'}), 400

        try:
            cursor.execute("INSERT INTO PURPOSES (PURPOSE_NAME) VALUES (%s)", (purpose_name,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Purpose added successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    # GET method
    try:
        cursor.execute("SELECT PURPOSE_ID, PURPOSE_NAME FROM PURPOSES ORDER BY PURPOSE_NAME")
        purposes = cursor.fetchall()
        return jsonify([{
            'PURPOSE_ID': purpose[0],
            'PURPOSE_NAME': purpose[1]
        } for purpose in purposes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/purposes/<int:purpose_id>', methods=['DELETE'])
def delete_purpose(purpose_id):
    if 'IDNO' not in session or session['USER_TYPE'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM PURPOSES WHERE PURPOSE_ID = %s", (purpose_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Purpose deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

