from flask import Blueprint, render_template, request, jsonify
from db import get_db_connection

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html', admin_email='admin@example.com')

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
