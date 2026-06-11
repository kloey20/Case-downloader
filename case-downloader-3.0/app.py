from flask import Flask, render_template, request, jsonify
import os
import uuid
import threading
import queue
import tkinter as tk
from tkinter import filedialog
from download import LawPhilDownloader

app = Flask(__name__)

# --- BACKGROUND WORKER QUEUE ---
batch_tasks = {}
task_queue = queue.Queue()

def process_worker():
    """Continuously runs in the background, processing cases one by one."""
    while True:
        task_id, case_num, folder = task_queue.get()
        if task_id is None: break
        
        batch_tasks[task_id]['status'] = 'processing'
        downloader = LawPhilDownloader(headless=True)
        
        try:
            # Performs the search, cleans the cookies, and saves the file automatically
            pdf_path = downloader.process_and_download(case_num, folder)
            
            if pdf_path and os.path.exists(pdf_path):
                batch_tasks[task_id].update({'status': 'completed', 'path': pdf_path})
            else:
                batch_tasks[task_id]['status'] = 'not_found'
        except Exception:
            batch_tasks[task_id]['status'] = 'error'
            
        task_queue.task_done()

# Start background thread
threading.Thread(target=process_worker, daemon=True).start()


# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/select_folder')
def select_folder():
    """Opens a native Windows directory picker"""
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    folder_path = filedialog.askdirectory()
    root.destroy()
    return jsonify({"folder": folder_path})

@app.route('/add_to_queue', methods=['POST'])
def add_to_queue():
    """Receives a case number and adds it to the background processing queue."""
    case_num = request.form.get('case_number')
    folder = request.form.get('output_folder')
    
    if not case_num: 
        return jsonify({'success': False})
    
    task_id = str(uuid.uuid4())
    batch_tasks[task_id] = {
        'id': task_id, 
        'number': case_num, 
        'status': 'queued',
        'path': None
    }
    
    # Send to the background worker
    task_queue.put((task_id, case_num, folder))
    return jsonify({'success': True})

@app.route('/queue_status')
def queue_status():
    """Returns the current status of all tasks for the UI to update."""
    return jsonify(batch_tasks)

if __name__ == '__main__':
    app.run(debug=True)