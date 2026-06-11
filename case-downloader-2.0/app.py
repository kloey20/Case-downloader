from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
from download import LawPhilDownloader

app = Flask(__name__)
app.secret_key = "lawphil_secret_key" # Required for flashing messages

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    # Gather form data
    input_text = request.form.get('input_text')
    is_url = request.form.get('is_url') == 'on'
    output_filename = request.form.get('output_filename')

    if not input_text:
        flash("Please enter a case number or URL.")
        return redirect(url_for('index'))

    # Initialize your downloader (force headless for web server)
    downloader = LawPhilDownloader(headless=True)
    
    try:
        if is_url:
            pdf_path = downloader.download_from_url(input_text, output_filename)
        else:
            pdf_path = downloader.download_case(input_text, output_filename)

        if pdf_path and os.path.exists(pdf_path):
            # Send the file to the user's browser, then you can optionally clean it up
            return send_file(pdf_path, as_attachment=True)
        else:
            flash("Failed to download the case. Ensure the case number or URL is correct.")
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Runs on http://127.0.0.1:5000
    app.run(debug=True)