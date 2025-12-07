import flask
from flask import jsonify, request
from mysql.connector import Error
import creds
from sql import create_connection, execute_read_query

app = flask.Flask(__name__)
app.config["DEBUG"] = True


# ---------- DB Connection Helper ----------

def get_conn():
    """Create connection to the database using values from creds.py"""
    myCreds = creds.Creds()
    return create_connection(
        myCreds.conString,
        myCreds.userName,
        myCreds.password,
        myCreds.dbName
    )


# ---------- Validation Helpers ----------

def validate_ingredient_payload(data, creating=True):
    """
    Validate payload for ingredient create/update.
    Required fields on create: ingredientname, totalamount
    On update: at least one of them.
    """
    required = ["ingredientname", "totalamount"]

    if creating:
        missing = [k for k in required if k not in data]
        if missing:
            return False, f"Missing fields: {', '.join(missing)}"
    else:
        if not any(k in data for k in required):
            return False, "No updatable fields provided."

    # type check for totalamount if present
    if "totalamount" in data:
        try:
            int(data["totalamount"])
        except (TypeError, ValueError):
            return False, "totalamount must be an integer."

    return True, None


def validate_recipe_payload(data, creating=True):
    """
    Validate payload for recipe create/update.
    Required fields on create: name, instructions.
    On update: at least one of them.
    """
    required = ["name", "instructions"]

    if creating:
        missing = [k for k in required if k not in data]
        if missing:
            return False, f"Missing fields: {', '.join(missing)}"
    else:
        if not any(k in data for k in required):
            return False, "No updatable fields provided."

    return True, None


def validate_recipeingredient_payload(data, creating=True):
    """
    Validate payload for recipeingredient create/update.
    Required fields on create: recipeid, ingredientid, amount.
    On update: at least one of them.
    """
    required = ["recipeid", "ingredientid", "amount"]

    if creating:
        missing = [k for k in required if k not in data]
        if missing:
            return False, f"Missing fields: {', '.join(missing)}"
    else:
        if not any(k in data for k in required):
            return False, "No updatable fields provided."

    # amount must be integer if present
    if "amount" in data:
        try:
            int(data["amount"])
        except (TypeError, ValueError):
            return False, "amount must be an integer."

    return True, None


# ---------- Fetch Helpers ----------

def fetch_one_ingredient(ingredient_id):
    """Return one ingredient row as dict or None."""
    conn = get_conn()
    if not conn:
        return None, "Database connection failed."

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, ingredientname, totalamount
            FROM ingredient
            WHERE id = %s
            """,
            (ingredient_id,)
        )
        row = cur.fetchone()
        return row, None
    except Error as e:
        return None, str(e)
    finally:
        conn.close()


def fetch_one_recipe(recipe_id):
    """Return one recipe row as dict or None."""
    conn = get_conn()
    if not conn:
        return None, "Database connection failed."

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, name, instructions
            FROM recipe
            WHERE id = %s
            """,
            (recipe_id,)
        )
        row = cur.fetchone()
        return row, None
    except Error as e:
        return None, str(e)
    finally:
        conn.close()


def fetch_one_recipeingredient(ri_id):
    """Return one recipeingredient row as dict or None."""
    conn = get_conn()
    if not conn:
        return None, "Database connection failed."

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, recipeid, ingredientid, amount
            FROM recipeingredient
            WHERE id = %s
            """,
            (ri_id,)
        )
        row = cur.fetchone()
        return row, None
    except Error as e:
        return None, str(e)
    finally:
        conn.close()


# ---------- Basic Routes ----------

@app.route('/', methods=['GET'])
def home():
    return "<h1> Recipe Manager API (Sprint 1) </h1>"


@app.route('/health', methods=['GET'])
def health():
    """Simple health check for backend + DB connectivity."""
    conn = get_conn()
    if conn:
        conn.close()
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "db_unreachable"}), 503


# ======================================================
# INGREDIENTS
# ======================================================

# READ ALL
@app.route('/ingredients', methods=['GET'])
def get_ingredients():
    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        sql = "SELECT id, ingredientname, totalamount FROM ingredient ORDER BY id"
        rows = execute_read_query(conn, sql)
        return jsonify(rows), 200
    except Error as e:
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# CREATE
@app.route('/ingredients', methods=['POST'])
def create_ingredient():
    data = request.get_json(silent=True) or request.form.to_dict()
    ok, err = validate_ingredient_payload(data, creating=True)
    if not ok:
        return jsonify({"error": err}), 400

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        sql = """
            INSERT INTO ingredient (ingredientname, totalamount)
            VALUES (%s, %s)
        """
        args = (
            data["ingredientname"],
            int(data["totalamount"])
        )
        cur = conn.cursor()
        cur.execute(sql, args)
        new_id = cur.lastrowid
        conn.commit()
        return jsonify({
            "id": new_id,
            "ingredientname": data["ingredientname"],
            "totalamount": int(data["totalamount"])
        }), 201
    except Error as e:
        conn.rollback()
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# READ ONE
@app.route('/ingredients/<int:ingredient_id>', methods=['GET'])
def get_ingredient(ingredient_id):
    row, db_err = fetch_one_ingredient(ingredient_id)
    if db_err:
        return jsonify({"error": f"DB error: {db_err}"}), 500
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(row), 200


# UPDATE
@app.route('/ingredients/<int:ingredient_id>', methods=['PUT'])
def update_ingredient(ingredient_id):
    exists, db_err = fetch_one_ingredient(ingredient_id)
    if db_err:
        return jsonify({"error": f"DB error: {db_err}"}), 500
    if not exists:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or request.form.to_dict()
    ok, err = validate_ingredient_payload(data, creating=False)
    if not ok:
        return jsonify({"error": err}), 400

    sets, args = [], []
    for col in ["ingredientname", "totalamount"]:
        if col in data:
            if col == "totalamount":
                try:
                    data[col] = int(data[col])
                except (TypeError, ValueError):
                    return jsonify({"error": "totalamount must be an integer."}), 400
            sets.append(f"{col} = %s")
            args.append(data[col])

    if not sets:
        return jsonify({"error": "No updatable fields provided."}), 400

    args.append(ingredient_id)

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        sql = f"UPDATE ingredient SET {', '.join(sets)} WHERE id = %s"
        cur = conn.cursor()
        cur.execute(sql, tuple(args))
        conn.commit()
        return jsonify({"message": "Updated"}), 200
    except Error as e:
        conn.rollback()
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# DELETE
@app.route('/ingredients/<int:ingredient_id>', methods=['DELETE'])
def delete_ingredient(ingredient_id):
    exists, db_err = fetch_one_ingredient(ingredient_id)
    if db_err:
        return jsonify({"error": f"DB error: {db_err}"}), 500
    if not exists:
        return jsonify({"error": "Not found"}), 404

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM ingredient WHERE id = %s", (ingredient_id,))
        conn.commit()
        return jsonify({"message": "Deleted"}), 200
    except Error as e:
        conn.rollback()
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# ======================================================
# RECIPES
# ======================================================

# READ ALL
@app.route('/recipes', methods=['GET'])
def get_recipes():
    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        sql = "SELECT id, name, instructions FROM recipe ORDER BY id"
        rows = execute_read_query(conn, sql)
        return jsonify(rows), 200
    except Error as e:
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# CREATE
@app.route('/recipes', methods=['POST'])
def create_recipe():
    data = request.get_json(silent=True) or request.form.to_dict()
    ok, err = validate_recipe_payload(data, creating=True)
    if not ok:
        return jsonify({"error": err}), 400

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        sql = "INSERT INTO recipe (name, instructions) VALUES (%s, %s)"
        args = (data["name"], data["instructions"])
        cur = conn.cursor()
        cur.execute(sql, args)
        new_id = cur.lastrowid
        conn.commit()
        return jsonify({
            "id": new_id,
            "name": data["name"],
            "instructions": data["instructions"]
        }), 201
    except Error as e:
        conn.rollback()
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# READ ONE
@app.route('/recipes/<int:recipe_id>', methods=['GET'])
def get_recipe(recipe_id):
    row, db_err = fetch_one_recipe(recipe_id)
    if db_err:
        return jsonify({"error": f"DB error: {db_err}"}), 500
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(row), 200


# UPDATE
@app.route('/recipes/<int:recipe_id>', methods=['PUT'])
def update_recipe(recipe_id):
    exists, db_err = fetch_one_recipe(recipe_id)
    if db_err:
        return jsonify({"error": f"DB error: {db_err}"}), 500
    if not exists:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or request.form.to_dict()
    ok, err = validate_recipe_payload(data, creating=False)
    if not ok:
        return jsonify({"error": err}), 400

    sets, args = [], []
    for col in ["name", "instructions"]:
        if col in data:
            sets.append(f"{col} = %s")
            args.append(data[col])

    if not sets:
        return jsonify({"error": "No updatable fields provided."}), 400

    args.append(recipe_id)

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        sql = f"UPDATE recipe SET {', '.join(sets)} WHERE id = %s"
        cur = conn.cursor()
        cur.execute(sql, tuple(args))
        conn.commit()
        return jsonify({"message": "Updated"}), 200
    except Error as e:
        conn.rollback()
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# DELETE
@app.route('/recipes/<int:recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    exists, db_err = fetch_one_recipe(recipe_id)
    if db_err:
        return jsonify({"error": f"DB error: {db_err}"}), 500
    if not exists:
        return jsonify({"error": "Not found"}), 404

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM recipe WHERE id = %s", (recipe_id,))
        conn.commit()
        return jsonify({"message": "Deleted"}), 200
    except Error as e:
        conn.rollback()
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# ======================================================
# RECIPEINGREDIENTS
# ======================================================

# READ (by recipeid query param)
@app.route('/recipeingredients', methods=['GET'])
def get_recipeingredients():
    recipe_id = request.args.get('recipeid')
    if not recipe_id:
        return jsonify({"error": "recipeid is required"}), 400

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        sql = """
            SELECT r.name AS recipe,
                   i.ingredientname,
                   ri.amount
        FROM recipeingredient ri
        JOIN ingredient i ON i.id = ri.ingredientid
        JOIN recipe r     ON r.id = ri.recipeid
        WHERE ri.recipeid = %s
        """
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, (recipe_id,))
        rows = cur.fetchall()
        return jsonify(rows), 200
    except Error as e:
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# CREATE
@app.route('/recipeingredients', methods=['POST'])
def create_recipeingredient():
    data = request.get_json(silent=True) or request.form.to_dict()
    ok, err = validate_recipeingredient_payload(data, creating=True)
    if not ok:
        return jsonify({"error": err}), 400

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        sql = """
            INSERT INTO recipeingredient (recipeid, ingredientid, amount)
            VALUES (%s, %s, %s)
        """
        args = (
            int(data["recipeid"]),
            int(data["ingredientid"]),
            int(data["amount"])
        )
        cur = conn.cursor()
        cur.execute(sql, args)
        new_id = cur.lastrowid
        conn.commit()
        return jsonify({
            "id": new_id,
            "recipeid": int(data["recipeid"]),
            "ingredientid": int(data["ingredientid"]),
            "amount": int(data["amount"])
        }), 201
    except Error as e:
        conn.rollback()
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# READ ONE
@app.route('/recipeingredients/<int:ri_id>', methods=['GET'])
def get_recipeingredient(ri_id):
    row, db_err = fetch_one_recipeingredient(ri_id)
    if db_err:
        return jsonify({"error": f"DB error: {db_err}"}), 500
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(row), 200


# UPDATE
@app.route('/recipeingredients/<int:ri_id>', methods=['PUT'])
def update_recipeingredient(ri_id):
    exists, db_err = fetch_one_recipeingredient(ri_id)
    if db_err:
        return jsonify({"error": f"DB error: {db_err}"}), 500
    if not exists:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or request.form.to_dict()
    ok, err = validate_recipeingredient_payload(data, creating=False)
    if not ok:
        return jsonify({"error": err}), 400

    sets, args = [], []
    for col in ["recipeid", "ingredientid", "amount"]:
        if col in data:
            if col in ["recipeid", "ingredientid", "amount"]:
                try:
                    data[col] = int(data[col])
                except (TypeError, ValueError):
                    return jsonify({"error": f"{col} must be an integer."}), 400
            sets.append(f"{col} = %s")
            args.append(data[col])

    if not sets:
        return jsonify({"error": "No updatable fields provided."}), 400

    args.append(ri_id)

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        sql = f"UPDATE recipeingredient SET {', '.join(sets)} WHERE id = %s"
        cur = conn.cursor()
        cur.execute(sql, tuple(args))
        conn.commit()
        return jsonify({"message": "Updated"}), 200
    except Error as e:
        conn.rollback()
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# DELETE
@app.route('/recipeingredients/<int:ri_id>', methods=['DELETE'])
def delete_recipeingredient(ri_id):
    exists, db_err = fetch_one_recipeingredient(ri_id)
    if db_err:
        return jsonify({"error": f"DB error: {db_err}"}), 500
    if not exists:
        return jsonify({"error": "Not found"}), 404

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM recipeingredient WHERE id = %s", (ri_id,))
        conn.commit()
        return jsonify({"message": "Deleted"}), 200
    except Error as e:
        conn.rollback()
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        conn.close()


# ======================================================
# COOK ENDPOINT (your original logic, reused)
# ======================================================

@app.route('/cook', methods=['POST'])
def cook_recipe():
    data = request.get_json(silent=True) or request.form.to_dict()
    if 'recipeid' not in data:
        return jsonify({"error": "recipeid required"}), 400

    recipe_id = data['recipeid']

    conn = get_conn()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    cur = conn.cursor(dictionary=True)

    try:
        # Get ingredient requirements for this recipe
        cur.execute("""
            SELECT ri.ingredientid, ri.amount, i.totalamount
            FROM recipeingredient ri
            JOIN ingredient i ON i.id = ri.ingredientid
            WHERE ri.recipeid = %s
        """, (recipe_id,))
        ingredients = cur.fetchall()

        if not ingredients:
            return jsonify({"error": "recipe not found or has no ingredients"}), 404

        # Check if we have enough ingredients
        for item in ingredients:
            if item['totalamount'] < item['amount']:
                return jsonify({
                    "can_cook": False,
                    "message": "Not enough ingredients to cook this recipe."
                }), 200

        # Deduct the amounts from inventory
        for item in ingredients:
            new_amt = item['totalamount'] - item['amount']
            cur.execute(
                "UPDATE ingredient SET totalamount = %s WHERE id = %s",
                (new_amt, item['ingredientid'])
            )
        conn.commit()

        return jsonify({
            "can_cook": True,
            "message": "Cooked successfully. Inventory updated."
        }), 200
    except Error as e:
        conn.rollback()
        return jsonify({"error": f"DB error: {e}"}), 500
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    app.run(port=5001)
