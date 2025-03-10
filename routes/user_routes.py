from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from db import get_db_connection
import os
from werkzeug.utils import secure_filename
import base64
from io import BytesIO
from datetime import datetime, timedelta

user_bp = Blueprint('user', __name__)

# Add configuration for file uploads
UPLOAD_FOLDER = 'static/profile_pictures'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@user_bp.route('/update_profile_picture', methods=['POST'])
def update_profile_picture():
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    if 'profile_picture' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        # Read the file content
        file_content = file.read()
        
        # Update the user's profile picture in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE USERS SET PROFILE_PICTURE = %s WHERE IDNO = %s",
                (file_content, session['IDNO'])
            )
            conn.commit()
            
            # Convert image to base64 for immediate display
            encoded_image = base64.b64encode(file_content).decode('utf-8')
            
            return jsonify({
                'success': True,
                'profile_picture_data': f"data:image/{file.filename.split('.')[-1]};base64,{encoded_image}"
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    return jsonify({'error': 'Invalid file type'}), 400

@user_bp.route('/get_profile_picture/<string:idno>')
def get_profile_picture(idno):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT PROFILE_PICTURE FROM USERS WHERE IDNO = %s", (idno,))
        result = cursor.fetchone()
        if result and result[0]:
            return send_file(
                BytesIO(result[0]),
                mimetype='image/jpeg'
            )
        else:
            # Return a default profile picture from static folder
            return redirect(url_for('static', filename='static/images/default-profile.png'))
    except Exception as e:
        # Return a default profile picture from static folder
        return redirect(url_for('static', filename='static/images/default-profile.png'))
    finally:
        cursor.close()
        conn.close()

@user_bp.route('/edit_info', methods=['GET', 'POST'])
def edit_info():
    if 'IDNO' in session:
        user_idno = session['IDNO']
        firstname = session['FIRSTNAME']
        lastname = session['LASTNAME']
        middlename = session['MIDDLENAME']
        course = session['COURSE']
        year = session['YEAR']
        email = session['EMAIL']

        if request.method == 'POST':
            new_firstname = request.form['firstname']
            
            new_lastname = request.form['lastname']
            new_middlename = request.form['middlename']
            new_course = request.form['course']
            new_year = request.form['year']
            new_email = request.form['email']

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""UPDATE USERS SET FIRSTNAME = %s, LASTNAME = %s, MIDDLENAME = %s, COURSE = %s, YEAR = %s, EMAIL = %s WHERE IDNO = %s""",
                           (new_firstname, new_lastname, new_middlename, new_course, new_year, new_email, user_idno))

            conn.commit()
            cursor.close()
            conn.close()

            session['FIRSTNAME'] = new_firstname
            session['LASTNAME'] = new_lastname
            session['MIDDLENAME'] = new_middlename
            session['COURSE'] = new_course
            session['YEAR'] = new_year
            session['EMAIL'] = new_email

            flash('Your details have been updated successfully!', 'success')
            return redirect(url_for('user.dashboard'))

        return render_template('edit_info.html', user_idno=user_idno, firstname=firstname, lastname=lastname,
                               middlename=middlename, course=course, year=year, email=email)
    else:
        flash('You must be logged in to edit your information.', 'error')
        return redirect(url_for('auth.login'))

@user_bp.route('/home')
def dashboard():
    if 'IDNO' in session:
        # First check user type and redirect if not a student
        if session.get('USER_TYPE') == 'ADMIN':
            return redirect(url_for('admin.admin_dashboard'))
        elif session.get('USER_TYPE') == 'STAFF':
            return redirect(url_for('staff.dashboard'))
        
        # Continue with student dashboard if user is a student
        user_idno = session['IDNO']
        firstname = session.get('FIRSTNAME')
        lastname = session.get('LASTNAME')
        middlename = session.get('MIDDLENAME')
        course = session.get('COURSE')
        year = session.get('YEAR')
        email = session.get('EMAIL')

        # Get remaining sit-in sessions
        remaining_sessions = 0
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT SIT_IN_COUNT FROM SIT_IN_LIMITS WHERE USER_IDNO = %s", (user_idno,))
            result = cursor.fetchone()
            if result:
                remaining_sessions = result[0]
        except Exception as e:
            print(f"Error getting remaining sessions: {e}")

        # Get announcements for student dashboard
        try:
            cursor.execute("""
                SELECT ANNOUNCEMENT_ID, TITLE, CONTENT, DATE_POSTED, POSTED_BY 
                FROM ANNOUNCEMENTS 
                ORDER BY DATE_POSTED DESC
            """)
            announcements_data = cursor.fetchall()
            ann_list = []
            for ann in announcements_data:
                ann_date = ann[3]
                if hasattr(ann_date, 'strftime'):
                    date_str = ann_date.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    date_str = ann_date
                ann_list.append({
                    'announcement_id': ann[0],
                    'title': ann[1],
                    'content': ann[2],
                    'date_posted': date_str,
                    'posted_by': ann[4]
                })
        except Exception as e:
            ann_list = []
        finally:
            cursor.close()
            conn.close()

        # Group announcements by time period
        grouped_announcements = group_announcements_by_time(ann_list)
        return render_template('dashboard.html', 
                            user_idno=user_idno,
                            firstname=firstname,
                            middlename=middlename,
                            lastname=lastname,
                            course=course,
                            year=year,
                            email=email,
                            remaining_sessions=remaining_sessions,
                            grouped_announcements=grouped_announcements)
    else:
        flash('You must be logged in to view the dashboard.', 'error')
        return redirect(url_for('auth.login'))

def group_announcements_by_time(announcements):
    """
    Group announcements into categories:
      - "This Week" (from Monday of the current week)
      - "Last Week"
      - "Last Month"
      - "Earlier"
    """
    now = datetime.now()
    # Get Monday of the current week
    this_week_start = now - timedelta(days=now.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(seconds=1)
    # Last month: from first day of last month to last day of last month
    this_month_start = now.replace(day=1)
    last_month_end = this_month_start - timedelta(seconds=1)
    last_month_start = last_month_end.replace(day=1)
    
    grouped = {
        "This Week": [],
        "Last Week": [],
        "Last Month": [],
        "Earlier": []
    }
    for ann in announcements:
        try:
            dt = datetime.strptime(ann['date_posted'], "%Y-%m-%d %H:%M:%S")
        except Exception:
            # If parsing fails, skip grouping for this announcement.
            dt = now
        if dt >= this_week_start:
            grouped["This Week"].append(ann)
        elif last_week_start <= dt <= last_week_end:
            grouped["Last Week"].append(ann)
        elif last_month_start <= dt <= last_month_end:
            grouped["Last Month"].append(ann)
        else:
            grouped["Earlier"].append(ann)
    return grouped

@user_bp.route('/get_announcements')
def get_announcements():
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT ANNOUNCEMENT_ID, TITLE, CONTENT, DATE_POSTED, POSTED_BY 
            FROM ANNOUNCEMENTS 
            ORDER BY DATE_POSTED DESC
        """)
        announcements_data = cursor.fetchall()
        ann_list = []
        for ann in announcements_data:
            ann_date = ann[3]
            if hasattr(ann_date, 'strftime'):
                date_str = ann_date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = ann_date
            ann_list.append({
                'announcement_id': ann[0],
                'title': ann[1],
                'content': ann[2],
                'date_posted': date_str,
                'posted_by': ann[4]
            })
        
        # Group announcements by time period
        grouped_announcements = group_announcements_by_time(ann_list)
        return jsonify({'grouped_announcements': grouped_announcements})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@user_bp.route('/sitin_records')
def get_student_sitin_records():
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    lab_id = request.args.get('lab_id')
    purpose_id = request.args.get('purpose_id')
    status = request.args.get('status')
    session_status = request.args.get('session')
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT s.RECORD_ID, s.USER_IDNO, s.LAB_ID, s.DATE, s.END_TIME, s.STATUS, s.SESSION,
                   l.LAB_NAME,
                   p.PURPOSE_NAME
            FROM SIT_IN_RECORDS s
            JOIN LABORATORIES l ON s.LAB_ID = l.LAB_ID
            JOIN PURPOSES p ON s.PURPOSE_ID = p.PURPOSE_ID
            WHERE s.USER_IDNO = %s
        """
        params = [session['IDNO']]

        if lab_id:
            query += " AND s.LAB_ID = %s"
            params.append(lab_id)
        
        if purpose_id:
            query += " AND s.PURPOSE_ID = %s"
            params.append(purpose_id)
            
        if status:
            query += " AND s.STATUS = %s"
            params.append(status)
            
        if session_status:
            query += " AND s.SESSION = %s"
            params.append(session_status)

        query += " ORDER BY s.DATE DESC"
        
        cursor.execute(query, params)
        records = cursor.fetchall()

        return jsonify([{
            'RECORD_ID': r[0],
            'STUDENT_ID': r[1],
            'LAB_ID': r[2],
            'DATE': r[3].isoformat(),
            'END_TIME': r[4].isoformat() if r[4] else None,
            'STATUS': r[5],
            'SESSION': r[6],
            'LAB_NAME': r[7],
            'PURPOSE_NAME': r[8]
        } for r in records])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@user_bp.route('/laboratories')
def get_laboratories():
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT LAB_ID, LAB_NAME FROM LABORATORIES")
        labs = cursor.fetchall()
        return jsonify([{'LAB_ID': lab[0], 'LAB_NAME': lab[1]} for lab in labs])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@user_bp.route('/purposes')
def get_purposes():
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT PURPOSE_ID, PURPOSE_NAME FROM PURPOSES ORDER BY PURPOSE_NAME")
        purposes = cursor.fetchall()
        return jsonify([{'PURPOSE_ID': purpose[0], 'PURPOSE_NAME': purpose[1]} for purpose in purposes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@user_bp.route('/remaining_sessions')
def get_remaining_sessions():
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT SIT_IN_COUNT FROM SIT_IN_LIMITS WHERE USER_IDNO = %s", (session['IDNO'],))
        result = cursor.fetchone()
        return jsonify({'remaining_sessions': result[0] if result else 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()