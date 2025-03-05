from flask import Blueprint, request, jsonify, session
from db import get_db_connection

lab_bp = Blueprint('lab', __name__)

@lab_bp.route('/manage_labs', methods=['GET', 'POST', 'DELETE'])
def manage_labs():
    if 'USER_TYPE' in session and session['USER_TYPE'] == 'STAFF':
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            data = request.get_json()
            lab_id = data.get('lab_id')
            total_computers = data.get('total_computers')

            if not isinstance(total_computers, int) or total_computers <= 0:
                return jsonify({'error': 'Invalid number of computers'}), 400

            if lab_id:
                cursor.execute("SELECT COUNT(*) FROM LABORATORIES WHERE LAB_ID = %s", (lab_id,))
                if cursor.fetchone()[0] > 0:
                    return jsonify({'error': 'Lab ID already exists'}), 400
                
                cursor.execute("INSERT INTO LABORATORIES (LAB_ID, TOTAL_COMPUTERS) VALUES (%s, %s)", 
                               (lab_id, total_computers))
            else:
                cursor.execute("INSERT INTO LABORATORIES (TOTAL_COMPUTERS) VALUES (%s)", (total_computers,))
                lab_id = cursor.lastrowid  

            for _ in range(total_computers):
                cursor.execute("INSERT INTO COMPUTERS (LAB_ID) VALUES (%s)", (lab_id,))

            conn.commit()
            return jsonify({'message': 'Laboratory and computers added successfully'}), 201

        elif request.method == 'GET':
            cursor.execute("""
                SELECT L.LAB_ID, COUNT(C.COMPUTER_ID) AS TOTAL_COMPUTERS
                FROM LABORATORIES L
                LEFT JOIN COMPUTERS C ON L.LAB_ID = C.LAB_ID
                GROUP BY L.LAB_ID
            """)
            labs = cursor.fetchall()
            lab_list = [{'LAB_ID': lab[0], 'TOTAL_COMPUTERS': lab[1]} for lab in labs]

            cursor.close()
            conn.close()
            return jsonify(lab_list)

        elif request.method == 'DELETE':
            data = request.get_json()
            lab_id = data.get('lab_id')

            if not lab_id:
                return jsonify({'error': 'Missing lab_id'}), 400

            # Delete all computers in the lab
            cursor.execute("DELETE FROM COMPUTERS WHERE LAB_ID = %s", (lab_id,))
            # Delete the lab itself
            cursor.execute("DELETE FROM LABORATORIES WHERE LAB_ID = %s", (lab_id,))
            conn.commit()

            return jsonify({'message': 'Laboratory and all its computers deleted successfully'}), 200

    return jsonify({'error': 'Access denied'}), 403


@lab_bp.route('/search_student/<idno>', methods=['GET'])
def search_student(idno):
    if not idno:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT IDNO, LASTNAME, FIRSTNAME, EMAIL, COURSE, YEAR FROM USERS WHERE IDNO = %s AND USER_TYPE = 'STUDENT'", (idno,))
        student = cursor.fetchone()
        
        if student:
            student_data = {
                "IDNO": student[0],
                "NAME": f"{student[2]} {student[1]}",
                "EMAIL": student[3],
                "COURSE": student[4],
                "YEAR": student[5]
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
                    "INSERT INTO ANNOUNCEMENTS (TITLE, CONTENT, POSTED_BY) VALUES (%s, %s, %s)",
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
    return jsonify({'error': 'Access denied'}), 403

@lab_bp.route('/announcements/<int:announcement_id>', methods=['PUT', 'DELETE'])
def manage_announcement(announcement_id):
    if 'USER_TYPE' in session and session['USER_TYPE'] in ['STAFF', 'ADMIN']:
        conn = get_db_connection()
        cursor = conn.cursor()
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