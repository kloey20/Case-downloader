from flask import Flask, render_template, request, jsonify
import os
from download import LawPhilDownloader

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    input_text = request.form.get('input_text')
    output_filename = request.form.get('output_filename')

    if not input_text:
        return jsonify({"success": False, "message": "Please enter a case number."})

    downloader = LawPhilDownloader(headless=True)
    
    try:
        # We only search by case number now
        pdf_path = downloader.download_case(input_text, output_filename)

        if pdf_path and os.path.exists(pdf_path):
            return jsonify({
                "success": True, 
                "message": f"Success! PDF saved to:\n{pdf_path}"
            })
        else:
            return jsonify({
                "success": False, 
                "message": "Failed to download the case. Ensure the case number is correct."
            })
            
    except Exception as e:
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True)