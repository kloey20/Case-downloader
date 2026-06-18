from flask import Flask, render_template, request, jsonify
import os
import uuid
import threading
import queue
import traceback
import tkinter as tk
from tkinter import filedialog
from download import LawPhilDownloader

app = Flask(__name__)

# --- BACKGROUND WORKER QUEUE ---
batch_tasks = {}
task_queue = queue.Queue()
tasks_lock = threading.Lock()  # Thread lock to safely update status across parallel browsers

# Parallel processing remains intact! 3 downloads will process simultaneously.
MAX_CONCURRENT_BROWSERS = 3

def process_worker():
    """Continuously runs in the background, processing cases. No auto-retry loop."""
    while True:
        item = task_queue.get()
        if item is None:
            task_queue.task_done()
            break
            
        task_id, case_num, folder = item

        # Update status to processing securely
        with tasks_lock:
            batch_tasks[task_id]["status"] = "processing"
            batch_tasks[task_id]["notes"] = "Processing download..."

        # Launches a brand new, clean independent Edge process for this worker thread
        downloader = LawPhilDownloader(headless=True)
        success = False
        error_msg = "Unknown error"

        try:
            pdf_path = downloader.process_and_download(case_num, folder)

            if pdf_path and os.path.exists(pdf_path):
                with tasks_lock:
                    batch_tasks[task_id].update({
                        "status": "completed", 
                        "path": pdf_path,
                        "notes": "Successfully downloaded."
                    })
                success = True
            else:
                error_msg = "File not found or failed to generate valid PDF layout."
        except Exception as exc:
            traceback.print_exc()
            error_msg = str(exc)
        finally:
            if not success:
                # If it fails, mark it as an error/not_found and stop. Do NOT re-queue automatically.
                with tasks_lock:
                    status_type = "error" if "error" in error_msg.lower() else "not_found"
                    batch_tasks[task_id].update({
                        "status": status_type,
                        "error": error_msg,
                        "notes": f"Failed: {error_msg}"
                    })

            task_queue.task_done()


# Start multiple background threads (The Worker Pool)
for _ in range(MAX_CONCURRENT_BROWSERS):
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
    with tasks_lock:
        batch_tasks[task_id] = {
            'id': task_id, 
            'number': case_num, 
            'status': 'queued',
            'path': None,
            'folder': folder,  # Saved so manual retries know where to save the file
            'notes': 'Waiting in queue...'
        }
    
    # Send to the background worker
    task_queue.put((task_id, case_num, folder))
    return jsonify({'success': True})

@app.route('/retry_task', methods=['POST'])
def retry_task():
    """Manually re-queues a failed task to execute fresh from the very beginning."""
    task_id = request.form.get('task_id')
    
    if not task_id:
        return jsonify({'success': False, 'error': 'Missing task_id'})
        
    with tasks_lock:
        if task_id not in batch_tasks:
            return jsonify({'success': False, 'error': 'Task not found'})
            
        task = batch_tasks[task_id]
        case_num = task['number']
        folder = task.get('folder', '')
        
        # Reset task state to queued exactly like a fresh input entry
        task.update({
            'status': 'queued',
            'path': None,
            'notes': 'Retrying... Waiting in queue.',
            'error': None
        })
        
    # Re-inject back into the thread worker stream
    task_queue.put((task_id, case_num, folder))
    return jsonify({'success': True})

@app.route('/queue_status')
def queue_status():
    """Returns the current status of all tasks for the UI to update."""
    with tasks_lock:
        return jsonify(batch_tasks)

if __name__ == '__main__':
    # use_reloader=False stops Flask from spawning duplicate threads on startup
    app.run(debug=True, use_reloader=False)