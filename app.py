from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route('/ask', methods=['POST'])
def ask():
    try:
        user_input = request.json.get("prompt", "")

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_input}],
            temperature=0.7,
        )

        return jsonify({
            "success": True,
            "response": response.choices[0].message["content"]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# For Railway
if __name__ == '__main__':
    app.run(debug=True)
