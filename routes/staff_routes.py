from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from db import get_db_connection
import os
from werkzeug.utils import secure_filename
import base64

staff_bp = Blueprint('staff', __name__)

# Add configuration for file uploads
UPLOAD_FOLDER = 'static/profile_pictures'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@staff_bp.route('/')
@staff_bp.route('/dashboard')
def staff_dashboard():
    if 'IDNO' not in session or session['USER_TYPE'] != 'STAFF':
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get all laboratories
        cursor.execute("SELECT * FROM LABORATORIES")
        laboratories = cursor.fetchall()

        # Get staff details
        cursor.execute("""
            SELECT FIRSTNAME, LASTNAME, EMAIL 
            FROM USERS 
            WHERE IDNO = %s
        """, (session['IDNO'],))
        staff_data = cursor.fetchone()

        return render_template('staff_dashboard.html', 
                             laboratories=[{
                                 'LAB_ID': lab[0],
                                 'LAB_NAME': lab[1]
                             } for lab in laboratories],
                             staff_firstname=staff_data[0],
                             staff_lastname=staff_data[1],
                             staff_email=staff_data[2])
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('auth.login'))
    finally:
        cursor.close()
        conn.close()

@staff_bp.route('/edit_info', methods=['GET', 'POST'])
def edit_info():
    if 'IDNO' in session and session['USER_TYPE'] == 'STAFF':
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Get all laboratories (needed for the template)
            cursor.execute("SELECT * FROM LABORATORIES")
            laboratories = cursor.fetchall()

            # Get current staff data
            cursor.execute("""
                SELECT FIRSTNAME, LASTNAME, EMAIL 
                FROM USERS 
                WHERE IDNO = %s
            """, (session['IDNO'],))
            staff_data = cursor.fetchone()

            if request.method == 'GET':
                return render_template('staff_dashboard.html',
                                    laboratories=[{
                                        'LAB_ID': lab[0],
                                        'LAB_NAME': lab[1]
                                    } for lab in laboratories],
                                    staff_firstname=staff_data[0],
                                    staff_lastname=staff_data[1],
                                    staff_email=staff_data[2])
            
            elif request.method == 'POST':
                new_firstname = request.form['firstname']
                new_lastname = request.form['lastname']
                new_email = request.form['email']
                new_password = request.form.get('password')

                try:
                    if new_password:
                        cursor.execute("""
                            UPDATE USERS 
                            SET FIRSTNAME = %s, LASTNAME = %s, EMAIL = %s, PASSWORD = %s 
                            WHERE IDNO = %s
                        """, (new_firstname, new_lastname, new_email, new_password, session['IDNO']))
                    else:
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

                    flash('Your details have been updated successfully!', 'success')
                except Exception as e:
                    flash(f'An error occurred: {str(e)}', 'error')

                return redirect(url_for('staff.staff_dashboard'))

        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('auth.login'))
        finally:
            cursor.close()
            conn.close()

    flash('You must be logged in as staff to edit information.', 'error')
    return redirect(url_for('auth.login'))

@staff_bp.route('/update_profile_picture', methods=['POST'])
def update_profile_picture():
    if 'IDNO' not in session or session.get('USER_TYPE') != 'STAFF':
        return jsonify({'error': 'Unauthorized'}), 401

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

@staff_bp.route('/start_sitin', methods=['POST'])
def start_sitin():
    if 'IDNO' not in session or session['USER_TYPE'] != 'STAFF':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    student_id = data.get('student_id')
    lab_id = data.get('lab_id')
    purpose_id = data.get('purpose_id')

    if not all([student_id, lab_id, purpose_id]):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if student has an ongoing sit-in session
        cursor.execute("""
            SELECT COUNT(*) FROM SIT_IN_RECORDS 
            WHERE USER_IDNO = %s AND SESSION = 'ON_GOING'
        """, (student_id,))
        ongoing_sessions = cursor.fetchone()[0]
        if ongoing_sessions > 0:
            return jsonify({'error': 'Student already has an ongoing sit-in session'}), 400

        # Check student's sit-in limit
        cursor.execute("SELECT SIT_IN_COUNT FROM SIT_IN_LIMITS WHERE USER_IDNO = %s", (student_id,))
        result = cursor.fetchone()
        if not result or result[0] <= 0:
            return jsonify({'error': 'Student has no remaining sit-in sessions'}), 400

        # Get an available computer in the lab
        cursor.execute("""
            SELECT c.COMPUTER_ID 
            FROM COMPUTERS c
            LEFT JOIN SIT_IN_RECORDS s ON c.COMPUTER_ID = s.COMPUTER_ID AND s.SESSION = 'ON_GOING'
            WHERE c.LAB_ID = %s AND s.COMPUTER_ID IS NULL
            LIMIT 1
        """, (lab_id,))
        computer = cursor.fetchone()
        if not computer:
            return jsonify({'error': 'No available computers in this lab'}), 400

        # Start the sit-in session
        cursor.execute("""
            INSERT INTO SIT_IN_RECORDS 
            (USER_IDNO, LAB_ID, COMPUTER_ID, PURPOSE_ID, DATE, STATUS, SESSION)
            VALUES (%s, %s, %s, %s, NOW(), 'APPROVED', 'ON_GOING')
        """, (student_id, lab_id, computer[0], purpose_id))

        conn.commit()
        return jsonify({'success': True, 'message': 'Sit-in session started successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@staff_bp.route('/active_sessions')
def get_active_sessions():
    if 'IDNO' not in session or session['USER_TYPE'] != 'STAFF':
        return jsonify({'error': 'Unauthorized'}), 401

    lab_id = request.args.get('lab_id')
    purpose_id = request.args.get('purpose_id')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT s.RECORD_ID, s.USER_IDNO, s.LAB_ID, s.DATE, s.END_TIME,
                   u.FIRSTNAME, u.LASTNAME,
                   l.LAB_NAME,
                   p.PURPOSE_NAME
            FROM SIT_IN_RECORDS s
            JOIN USERS u ON s.USER_IDNO = u.IDNO
            JOIN LABORATORIES l ON s.LAB_ID = l.LAB_ID
            JOIN PURPOSES p ON s.PURPOSE_ID = p.PURPOSE_ID
            WHERE s.SESSION = 'ON_GOING'
        """
        params = []

        if lab_id:
            query += " AND s.LAB_ID = %s"
            params.append(lab_id)
        
        if purpose_id:
            query += " AND s.PURPOSE_ID = %s"
            params.append(purpose_id)

        cursor.execute(query, params)
        sessions = cursor.fetchall()

        return jsonify([{
            'RECORD_ID': s[0],
            'STUDENT_ID': s[1],
            'LAB_ID': s[2],
            'DATE': s[3].isoformat(),
            'END_TIME': s[4].isoformat() if s[4] else None,
            'STUDENT_NAME': f"{s[5]} {s[6]}",
            'LAB_NAME': s[7],
            'PURPOSE_NAME': s[8]
        } for s in sessions])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@staff_bp.route('/end_session/<int:record_id>', methods=['POST'])
def end_session(record_id):
    if 'IDNO' not in session or session['USER_TYPE'] != 'STAFF':
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get the student ID for the session
        cursor.execute("SELECT USER_IDNO FROM SIT_IN_RECORDS WHERE RECORD_ID = %s", (record_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({'error': 'Session not found'}), 404

        student_id = result[0]

        # Update the session status and set END_TIME
        cursor.execute("""
            UPDATE SIT_IN_RECORDS 
            SET SESSION = 'ENDED', END_TIME = NOW()
            WHERE RECORD_ID = %s
        """, (record_id,))

        # Decrease the student's sit-in limit
        cursor.execute("""
            UPDATE SIT_IN_LIMITS 
            SET SIT_IN_COUNT = SIT_IN_COUNT - 1 
            WHERE USER_IDNO = %s
        """, (student_id,))

        conn.commit()
        return jsonify({'success': True, 'message': 'Session ended successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@staff_bp.route('/laboratories')
def get_laboratories():
    if 'IDNO' not in session or session['USER_TYPE'] != 'STAFF':
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT LAB_ID, LAB_NAME FROM LABORATORIES")
        labs = cursor.fetchall()
        return jsonify([{
            'LAB_ID': lab[0],
            'LAB_NAME': lab[1]
        } for lab in labs])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@staff_bp.route('/purposes')
def get_purposes():
    if 'IDNO' not in session or session['USER_TYPE'] != 'STAFF':
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

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

@staff_bp.route('/check_remaining_sessions/<string:student_id>')
def check_remaining_sessions(student_id):
    if 'IDNO' not in session or session['USER_TYPE'] != 'STAFF':
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # First check if student exists and is actually a student
        cursor.execute("""
            SELECT IDNO FROM USERS 
            WHERE IDNO = %s AND USER_TYPE = 'STUDENT'
        """, (student_id,))
        
        if not cursor.fetchone():
            return jsonify({
                'error': 'Student not found',
                'remaining_sessions': 0
            }), 404

        # Get remaining sessions
        cursor.execute("""
            SELECT SIT_IN_COUNT 
            FROM SIT_IN_LIMITS 
            WHERE USER_IDNO = %s
        """, (student_id,))
        
        result = cursor.fetchone()
        if not result:
            return jsonify({
                'error': 'No sit-in limit found for student',
                'remaining_sessions': 0
            }), 404

        return jsonify({
            'remaining_sessions': result[0]
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'remaining_sessions': 0
        }), 500
    finally:
        cursor.close()
        conn.close()

@staff_bp.route('/sitin_records')
def get_sitin_records():
    if 'IDNO' not in session or session['USER_TYPE'] != 'STAFF':
        return jsonify({'error': 'Unauthorized'}), 401

    lab_id = request.args.get('lab_id')
    purpose_id = request.args.get('purpose_id')
    status = request.args.get('status')
    session_status = request.args.get('session')
    student_id = request.args.get('student_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT s.RECORD_ID, s.USER_IDNO, s.LAB_ID, s.DATE, s.END_TIME, s.STATUS, s.SESSION,
                   u.FIRSTNAME, u.LASTNAME,
                   l.LAB_NAME,
                   p.PURPOSE_NAME
            FROM SIT_IN_RECORDS s
            JOIN USERS u ON s.USER_IDNO = u.IDNO
            JOIN LABORATORIES l ON s.LAB_ID = l.LAB_ID
            JOIN PURPOSES p ON s.PURPOSE_ID = p.PURPOSE_ID
            WHERE 1=1
        """
        params = []

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

        if student_id:
            query += " AND s.USER_IDNO = %s"
            params.append(student_id)

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
            'STUDENT_NAME': f"{r[7]} {r[8]}",
            'LAB_NAME': r[9],
            'PURPOSE_NAME': r[10]
        } for r in records])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close() 