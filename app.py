from flask import Flask, request, jsonify
import openai
import json
import os
def load_env_file(path=".env.production"):
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if line.strip() == "" or line.startswith("#"):
                    continue
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

load_env_file()

from typing import Dict, Any

app = Flask(__name__)
openai.api_key = os.environ.get("OPENAI_API_KEY")


def calculate_xp(overall_score: int) -> int:
    """Calculate XP based on overall score"""
    if overall_score >= 90:
        return 35
    elif overall_score >= 80:
        return 30
    elif overall_score >= 70:
        return 25
    elif overall_score >= 60:
        return 20
    elif overall_score >= 50:
        return 15
    else:
        return 10

def create_evaluation_prompt(question_data: Dict, user_answer: str, role: str, experience_level: str) -> str:
    """Create the prompt for OpenAI evaluation"""
    
    expert_answer = question_data.get('answer', [])
    question_text = question_data.get('question', '')
    category = question_data.get('category', '')
    
    prompt = f"""
You are an expert cybersecurity interview evaluator. Please evaluate the following candidate's answer against the expert reference answer.

**Interview Context:**
- Role: {role}
- Experience Level: {experience_level}
- Question Category: {category}
- Question: {question_text}

**Expert Reference Answer:**
{json.dumps(expert_answer, indent=2)}

**Candidate's Answer:**
{user_answer}

**Evaluation Instructions:**
Please provide a detailed evaluation with the following scoring criteria:
- Coverage Score (0-30): How many key points from the expert answer were covered
- Technical Accuracy (0-30): Correctness of technical information provided
- Communication Quality (0-25): Clarity, structure, and professionalism of the response
- Additional Insights (0-15): Extra knowledge, best practices, or tools mentioned beyond the reference

**Required Response Format (JSON only):**
{{
    "overall_score": <sum of all breakdown scores>,
    "breakdown": {{
        "coverage_score": <0-30>,
        "technical_accuracy": <0-30>,
        "communication_quality": <0-25>,
        "additional_insights": <0-15>
    }},
    "feedback": {{
        "strengths": [<list of specific strengths observed>],
        "improvements": [<list of specific areas for improvement>],
        "specific_suggestions": [<list of actionable suggestions for improvement>]
    }},
    "expert_reference": {json.dumps(expert_answer)}
}}

Please respond with ONLY the JSON object, no additional text or explanation.
"""
    
    return prompt

@app.route('/api/evaluate', methods=['POST'])
def evaluate_answer():
    """Main endpoint for evaluating cybersecurity interview answers"""
    
    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    try:
        # Parse request data
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['question', 'user_answer', 'role', 'experience_level']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "MISSING_FIELD",
                        "message": f"Missing required field: {field}",
                        "details": f"The field '{field}' is required for evaluation"
                    }
                }), 400, headers
        
        # Extract data
        question_data = data['question']
        user_answer = data['user_answer']
        role = data['role']
        experience_level = data['experience_level']
        
        # Create evaluation prompt
        prompt = create_evaluation_prompt(question_data, user_answer, role, experience_level)
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert cybersecurity interview evaluator. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        # Parse OpenAI response
        ai_response = response.choices[0].message.content.strip()
        
        # Clean up response if it contains markdown formatting
        if ai_response.startswith('```json'):
            ai_response = ai_response[7:-3].strip()
        elif ai_response.startswith('```'):
            ai_response = ai_response[3:-3].strip()
        
        try:
            evaluation_data = json.loads(ai_response)
        except json.JSONDecodeError:
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_AI_RESPONSE",
                    "message": "Failed to parse AI evaluation response",
                    "details": "The AI response was not valid JSON"
                }
            }), 500, headers
        
        # Calculate XP
        overall_score = evaluation_data.get('overall_score', 0)
        xp_earned = calculate_xp(overall_score)
        
        # Prepare final response
        final_response = {
            "success": True,
            "evaluation": {
                "overall_score": overall_score,
                "breakdown": evaluation_data.get('breakdown', {}),
                "feedback": evaluation_data.get('feedback', {}),
                "expert_reference": evaluation_data.get('expert_reference', []),
                "xp_earned": xp_earned
            }
        }
        
        return jsonify(final_response), 200, headers
        
    except openai.RateLimitError:
        return jsonify({
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "OpenAI API rate limit exceeded",
                "details": "Please try again in a few minutes"
            }
        }), 429, headers
        
    except openai.AuthenticationError:
        return jsonify({
            "success": False,
            "error": {
                "code": "AUTHENTICATION_ERROR",
                "message": "OpenAI API authentication failed",
                "details": "Invalid API key or authentication issue"
            }
        }), 401, headers
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "EVALUATION_FAILED",
                "message": "Unable to evaluate the answer at this time",
                "details": str(e)
            }
        }), 500, headers

@app.route('/api/evaluate', methods=['OPTIONS'])
def handle_preflight():
    """Handle CORS preflight requests"""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    return '', 200, headers

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    return jsonify({
        "status": "healthy",
        "message": "Cybersecurity Interview Evaluation API is running"
    }), 200, headers

@app.route('/api', methods=['GET'])
def root():
    """Root endpoint with API information"""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    return jsonify({
        "name": "Cybersecurity Interview Evaluation API",
        "version": "1.0.0",
        "endpoints": {
            "evaluate": "POST /api/evaluate - Evaluate cybersecurity interview answers",
            "health": "GET /api/health - Health check"
        }
    }), 200, headers

# This is required for Vercel serverless functions
def handler(request):
    with app.test_request_context(request.path, method=request.method, headers=request.headers, data=request.body):
        return app.dispatch_request()

if __name__ == '__main__':
    # For local development only
    app.run(debug=True, host='0.0.0.0', port=5000)
