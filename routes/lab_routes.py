from flask import Blueprint, request, jsonify, session
from db import get_db_connection

lab_bp = Blueprint('lab', __name__)

@lab_bp.route('/manage_labs', methods=['GET', 'POST', 'DELETE'])
def manage_labs():
    if 'USER_TYPE' in session and (session['USER_TYPE'] == 'STAFF' or session['USER_TYPE'] == 'ADMIN'):
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            data = request.get_json()
            lab_name = data.get('lab_name')
            total_computers = data.get('total_computers')

            if not lab_name or not isinstance(total_computers, int) or total_computers <= 0:
                return jsonify({'error': 'Invalid lab name or number of computers'}), 400

            try:
                # Insert the lab
                cursor.execute("INSERT INTO LABORATORIES (LAB_NAME, TOTAL_COMPUTERS) VALUES (%s, %s)", 
                           (lab_name, total_computers))
                lab_id = cursor.lastrowid

                # Insert computers for the lab
                for i in range(total_computers):
                    cursor.execute("INSERT INTO COMPUTERS (LAB_ID) VALUES (%s)", 
                               (lab_id,))

                conn.commit()
                return jsonify({'message': 'Laboratory and computers added successfully', 'lab_id': lab_id}), 201
            except Exception as e:
                conn.rollback()
                return jsonify({'error': str(e)}), 500

        elif request.method == 'GET':
            cursor.execute("""
                SELECT L.LAB_ID, L.LAB_NAME, L.TOTAL_COMPUTERS, 
                       COUNT(C.COMPUTER_ID) AS AVAILABLE_COMPUTERS
                FROM LABORATORIES L
                LEFT JOIN COMPUTERS C ON L.LAB_ID = C.LAB_ID
                GROUP BY L.LAB_ID, L.LAB_NAME, L.TOTAL_COMPUTERS
                ORDER BY L.LAB_NAME
            """)
            labs = cursor.fetchall()
            lab_list = [{
                'LAB_ID': lab[0], 
                'LAB_NAME': lab[1],
                'TOTAL_COMPUTERS': lab[2],
                'AVAILABLE_COMPUTERS': lab[3] or 0
            } for lab in labs]

            cursor.close()
            conn.close()
            return jsonify(lab_list)

        elif request.method == 'DELETE':
            data = request.get_json()
            lab_id = data.get('lab_id')

            if not lab_id:
                return jsonify({'error': 'Missing lab_id'}), 400

            try:
                cursor.execute("DELETE FROM LABORATORIES WHERE LAB_ID = %s", (lab_id,))
                conn.commit()
                return jsonify({'message': 'Laboratory and all its computers deleted successfully'}), 200
            except Exception as e:
                conn.rollback()
                return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Access denied'}), 403


@lab_bp.route('/search_student/<idno>', methods=['GET'])
def search_student(idno):
    if not idno:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get student info
        cursor.execute("SELECT IDNO, LASTNAME, FIRSTNAME, EMAIL, COURSE, YEAR FROM USERS WHERE IDNO = %s AND USER_TYPE = 'STUDENT'", (idno,))
        student = cursor.fetchone()
        
        if student:
            # Get remaining sessions
            cursor.execute("SELECT SIT_IN_COUNT FROM SIT_IN_LIMITS WHERE USER_IDNO = %s", (idno,))
            sessions_result = cursor.fetchone()
            remaining_sessions = sessions_result[0] if sessions_result else 0
            
            student_data = {
                "IDNO": student[0],
                "NAME": f"{student[2]} {student[1]}",
                "EMAIL": student[3],
                "COURSE": student[4],
                "YEAR": student[5],
                "REMAINING_SESSIONS": remaining_sessions
            }
            return jsonify([student_data])
        else:
            return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
        
@lab_bp.route('/announcements', methods=['GET', 'POST'])
def announcements():
    # Only allow STAFF or ADMIN to manage announcements
    if 'USER_TYPE' in session and session['USER_TYPE'] in ['STAFF', 'ADMIN']:
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == 'POST':
            data = request.get_json()
            title = data.get('title')
            content = data.get('content')
            posted_by = session.get('IDNO')
            if not title or not content:
                return jsonify({'error': 'Title and content are required'}), 400
            try:
                cursor.execute(
                    "INSERT INTO ANNOUNCEMENTS (TITLE, CONTENT, POSTED_BY, DATE_POSTED) VALUES (%s, %s, %s, NOW())",
                    (title, content, posted_by)
                )
                conn.commit()
                return jsonify({'message': 'Announcement created successfully'}), 201
            except Exception as e:
                return jsonify({'error': str(e)}), 500
            finally:
                cursor.close()
                conn.close()
        else:  # GET
            try:
                cursor.execute("""
                    SELECT A.ANNOUNCEMENT_ID, A.TITLE, A.CONTENT, A.DATE_POSTED, A.POSTED_BY,
                           U.FIRSTNAME, U.LASTNAME
                    FROM ANNOUNCEMENTS A
                    JOIN USERS U ON A.POSTED_BY = U.IDNO
                    ORDER BY A.DATE_POSTED DESC
                """)
                announcements = cursor.fetchall()
                result = []
                for ann in announcements:
                    result.append({
                        'announcement_id': ann[0],
                        'title': ann[1],
                        'content': ann[2],
                        'date_posted': ann[3].strftime("%Y-%m-%d %H:%M:%S") if ann[3] else "",
                        'posted_by': ann[4],
                        'poster_name': f"{ann[5]} {ann[6]}"
                    })
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
            finally:
                cursor.close()
                conn.close()
    return jsonify({'error': 'Access denied'}), 403

@lab_bp.route('/announcements/<int:announcement_id>', methods=['PUT', 'DELETE'])
def manage_announcement(announcement_id):
    if 'USER_TYPE' in session and session['USER_TYPE'] in ['STAFF', 'ADMIN']:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First check if the announcement exists and belongs to the user
        cursor.execute("""
            SELECT POSTED_BY FROM ANNOUNCEMENTS 
            WHERE ANNOUNCEMENT_ID = %s
        """, (announcement_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'Announcement not found'}), 404
            
        # Only allow staff to edit/delete their own announcements (admin can edit/delete any)
        if session['USER_TYPE'] == 'STAFF' and result[0] != session['IDNO']:
            return jsonify({'error': 'You can only modify your own announcements'}), 403
            
        if request.method == 'PUT':
            data = request.get_json()
            title = data.get('title')
            content = data.get('content')
            if not title or not content:
                return jsonify({'error': 'Title and content are required'}), 400
            try:
                cursor.execute(
                    "UPDATE ANNOUNCEMENTS SET TITLE = %s, CONTENT = %s WHERE ANNOUNCEMENT_ID = %s",
                    (title, content, announcement_id)
                )
                conn.commit()
                return jsonify({'message': 'Announcement updated successfully'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
            finally:
                cursor.close()
                conn.close()
        elif request.method == 'DELETE':
            try:
                cursor.execute("DELETE FROM ANNOUNCEMENTS WHERE ANNOUNCEMENT_ID = %s", (announcement_id,))
                conn.commit()
                return jsonify({'message': 'Announcement deleted successfully'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
            finally:
                cursor.close()
                conn.close()
    return jsonify({'error': 'Access denied'}), 403

@lab_bp.route('/api/schedule', methods=['GET'])
def get_lab_schedule():
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                s.SCHEDULE_ID,
                s.LAB_ID,
                l.LAB_NAME,
                s.DAY_OF_WEEK,
                s.START_TIME,
                s.END_TIME,
                s.SUBJECT,
                s.INSTRUCTOR
            FROM LAB_SCHEDULE s
            JOIN LABORATORIES l ON s.LAB_ID = l.LAB_ID
            ORDER BY s.DAY_OF_WEEK, s.START_TIME
        """)
        
        schedule = []
        for row in cursor.fetchall():
            schedule.append({
                'schedule_id': row[0],
                'lab_id': row[1],
                'lab_name': row[2],
                'day': row[3],
                'start_time': row[4].strftime('%H:%M'),
                'end_time': row[5].strftime('%H:%M'),
                'subject': row[6],
                'instructor': row[7]
            })
            
        return jsonify(schedule)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@lab_bp.route('/api/schedule', methods=['POST'])
def add_lab_schedule():
    if 'IDNO' not in session or session['USER_TYPE'] not in ['STAFF', 'ADMIN']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    lab_id = data.get('lab_id')
    day = data.get('day')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    subject = data.get('subject')
    instructor = data.get('instructor')
    
    if not all([lab_id, day, start_time, end_time, subject, instructor]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO LAB_SCHEDULE 
            (LAB_ID, DAY_OF_WEEK, START_TIME, END_TIME, SUBJECT, INSTRUCTOR)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (lab_id, day, start_time, end_time, subject, instructor))
        
        conn.commit()
        return jsonify({'message': 'Schedule added successfully'}), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@lab_bp.route('/api/schedule/<int:schedule_id>', methods=['PUT'])
def update_lab_schedule(schedule_id):
    if 'IDNO' not in session or session['USER_TYPE'] not in ['STAFF', 'ADMIN']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    day = data.get('day')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    subject = data.get('subject')
    instructor = data.get('instructor')
    
    if not all([day, start_time, end_time, subject, instructor]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE LAB_SCHEDULE 
            SET DAY_OF_WEEK = %s,
                START_TIME = %s,
                END_TIME = %s,
                SUBJECT = %s,
                INSTRUCTOR = %s
            WHERE SCHEDULE_ID = %s
        """, (day, start_time, end_time, subject, instructor, schedule_id))
        
        conn.commit()
        return jsonify({'message': 'Schedule updated successfully'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@lab_bp.route('/api/schedule/<int:schedule_id>', methods=['DELETE'])
def delete_lab_schedule(schedule_id):
    if 'IDNO' not in session or session['USER_TYPE'] not in ['STAFF', 'ADMIN']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM LAB_SCHEDULE WHERE SCHEDULE_ID = %s", (schedule_id,))
        conn.commit()
        return jsonify({'message': 'Schedule deleted successfully'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()        