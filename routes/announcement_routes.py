from flask import Blueprint, request, jsonify, session
from db import get_db_connection
from datetime import datetime

announcement_bp = Blueprint('announcement', __name__)

@announcement_bp.route('/announcements', methods=['GET', 'POST'])
def announcements():
    if 'USER_TYPE' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        if session['USER_TYPE'] not in ['STAFF', 'ADMIN']:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        title = data.get('title')
        content = data.get('content')

        if not title or not content:
            return jsonify({'error': 'Title and content are required'}), 400

        try:
            cursor.execute("""
                INSERT INTO ANNOUNCEMENTS (TITLE, CONTENT, POSTED_BY, DATE_POSTED)
                VALUES (%s, %s, %s, NOW())
            """, (title, content, session['IDNO']))
            conn.commit()
            return jsonify({'message': 'Announcement posted successfully'}), 201
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500

    # GET method
    cursor.execute("""
        SELECT A.ANNOUNCEMENT_ID, A.TITLE, A.CONTENT, A.DATE_POSTED, 
               A.POSTED_BY, U.FIRST_NAME, U.LAST_NAME
        FROM ANNOUNCEMENTS A
        JOIN USERS U ON A.POSTED_BY = U.IDNO
        ORDER BY A.DATE_POSTED DESC
    """)
    announcements = cursor.fetchall()
    
    announcement_list = [{
        'announcement_id': ann[0],
        'title': ann[1],
        'content': ann[2],
        'date_posted': ann[3].strftime('%Y-%m-%d %H:%M:%S'),
        'posted_by': ann[4],
        'poster_name': f"{ann[5]} {ann[6]}",
        'can_edit': session.get('IDNO') == ann[4]
    } for ann in announcements]

    cursor.close()
    conn.close()
    return jsonify(announcement_list)

@announcement_bp.route('/announcements/<int:announcement_id>', methods=['PUT', 'DELETE'])
def manage_announcement(announcement_id):
    if 'USER_TYPE' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the announcement exists and belongs to the user
    cursor.execute("""
        SELECT POSTED_BY FROM ANNOUNCEMENTS 
        WHERE ANNOUNCEMENT_ID = %s
    """, (announcement_id,))
    result = cursor.fetchone()

    if not result:
        return jsonify({'error': 'Announcement not found'}), 404
    
    if result[0] != session['IDNO']:
        return jsonify({'error': 'Unauthorized to modify this announcement'}), 403

    try:
        if request.method == 'PUT':
            data = request.get_json()
            title = data.get('title')
            content = data.get('content')

            if not title or not content:
                return jsonify({'error': 'Title and content are required'}), 400

            cursor.execute("""
                UPDATE ANNOUNCEMENTS 
                SET TITLE = %s, CONTENT = %s 
                WHERE ANNOUNCEMENT_ID = %s
            """, (title, content, announcement_id))

        elif request.method == 'DELETE':
            cursor.execute("DELETE FROM ANNOUNCEMENTS WHERE ANNOUNCEMENT_ID = %s", (announcement_id,))

        conn.commit()
        return jsonify({'message': 'Announcement updated successfully'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close() 