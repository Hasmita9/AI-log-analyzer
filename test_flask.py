from flask import Flask, request, jsonify
from test_sdk import sdk
import logging

app = Flask(__name__)

items = [
    {"id": 1, "name": "Item 1"},
    {"id": 2, "name": "Item 2"}
]

# CREATE
@app.route('/items', methods=['POST'])
def create_item():
    data = request.get_json()
    if not data or not data.get("name"):
        logging.error("Create item failed: missing name field")
        return jsonify({"error": "Missing name"}), 400
    new_item = {"id": len(items) + 1, "name": data.get("name")}
    items.append(new_item)
    return jsonify({"message": "Item created", "item": new_item}), 201

# READ (All)
@app.route('/items', methods=['GET'])
def get_items():
    return jsonify(items), 200

# READ (Single)
@app.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    for item in items:
        if item["id"] == item_id:
            return jsonify(item), 200
    logging.error(f"Item not found: ID {item_id}")
    return jsonify({"error": "Item not found"}), 404

# UPDATE
@app.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.get_json()
    for item in items:
        if item["id"] == item_id:
            item["name"] = data.get("name", item["name"])
            return jsonify({"message": "Item updated", "item": item}), 200
    logging.error(f"Update failed: Item ID {item_id} not found")
    return jsonify({"error": "Item not found"}), 404

# DELETE
@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    for item in items:
        if item["id"] == item_id:
            items.remove(item)
            return jsonify({"message": "Item deleted"}), 200
    logging.error(f"Delete failed: Item ID {item_id} not found")
    return jsonify({"error": "Item not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='127.0.1.2', port=5002)