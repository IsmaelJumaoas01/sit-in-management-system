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
