from flask import Flask, request, redirect, render_template, flash, url_for, send_file
import os
import subprocess
import logging
import psutil
import mimetypes

# Configuración básica de logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.secret_key = 'supersecretkey'  # Necesario para usar flash

def get_unique_filename(directory, filename):
    base, extension = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(directory, unique_filename)):
        unique_filename = f"{base}_{counter}{extension}"
        counter += 1
    return unique_filename

@app.route('/')
def index():
    # Obtener datos del sistema usando psutil
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    memory_usage = memory_info.percent
    
    # Obtener información de la temperatura
    temperature_info = psutil.sensors_temperatures() if hasattr(psutil, 'sensors_temperatures') else {}
    core_temps = temperature_info.get('coretemp', [])
    core_temps = [sensor.current for sensor in core_temps]

    return render_template('index.html', cpu_usage=cpu_usage, memory_usage=memory_usage, core_temps=core_temps)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        filename = get_unique_filename(app.config['UPLOAD_FOLDER'], file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        app.logger.debug(f'File saved to {filepath}')
        try:
            compressed_filepath = compress_video(filepath)
            app.logger.debug(f'File compressed to {compressed_filepath}')
            compressed_filename = os.path.basename(compressed_filepath)
            return render_template('link.html', filename=compressed_filename)
        except Exception as e:
            app.logger.error(f'Error compressing file: {e}')
            return f'Error al comprimir el video: {e}', 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    mime_type, _ = mimetypes.guess_type(file_path)
    return send_file(file_path, mimetype=mime_type)

def compress_video(filepath):
    output_filepath = os.path.splitext(filepath)[0] + '_compressed.mp4'
    command = ['ffmpeg', '-i', filepath, '-vcodec', 'libx265', '-crf', '28', output_filepath]
    app.logger.debug(f'Running command: {" ".join(command)}')
    subprocess.run(command, check=True)
    return output_filepath

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(host='0.0.0.0', port=5000, debug=True)

