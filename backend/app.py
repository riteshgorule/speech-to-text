from flask import Flask, request, jsonify
import threading
import time
import subprocess
import sys
import websocket
import json
from urllib.parse import urlencode
import requests

app = Flask(__name__)

API_KEY = "c6bd1261617b4da7b503429a8a37e499"
ASSEMBLYAI_BASE = "https://api.assemblyai.com"

# ------------------ LIVE TRANSCRIPTION ------------------

FRAMES_PER_BUFFER = 800
CHANNELS = 1
SAMPLE_RATE = 16000

stop_event = threading.Event()
live_running = False

def ffmpeg_mic_stream():
    """Capture live mic input using FFmpeg."""
    if sys.platform.startswith("win"):
        mic_name = "Headset (realme Buds Wireless 3)"  # change your mic
        cmd = ["ffmpeg", "-f", "dshow", "-i", f"audio={mic_name}",
               "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "-f", "s16le", "-"]
    elif sys.platform.startswith("linux"):
        cmd = ["ffmpeg", "-f", "alsa", "-i", "default",
               "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "-f", "s16le", "-"]
    elif sys.platform.startswith("darwin"):
        cmd = ["ffmpeg", "-f", "avfoundation", "-i", ":0",
               "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "-f", "s16le", "-"]
    else:
        raise RuntimeError("Unsupported platform")
    return subprocess.Popen(cmd, stdout=subprocess.PIPE)

def start_live_transcription():
    """Start WebSocket live transcription."""
    # ensure previous stop_event is cleared before starting
    stop_event.clear()
    CONNECTION_PARAMS = {"sample_rate": SAMPLE_RATE, "format_turns": True}
    API_ENDPOINT = f"wss://streaming.assemblyai.com/v3/ws?{urlencode(CONNECTION_PARAMS)}"

    def on_open(ws):
        print("WebSocket opened. Start speaking...")

        def stream_audio():
            process = ffmpeg_mic_stream()
            # each sample is 16 bits = 2 bytes, times number of channels
            bytes_per_frame = 2 * CHANNELS
            chunk_size = FRAMES_PER_BUFFER * bytes_per_frame

            try:
                while not stop_event.is_set():
                    data = process.stdout.read(chunk_size)
                    if not data:
                        time.sleep(0.01)
                        continue
                    ws.send(data, websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                print(f"Stream audio error: {e}")
            finally:
                # ask AssemblyAI to terminate the session
                try:
                    ws.send(json.dumps({"type": "Terminate"}))
                except Exception:
                    pass
                # ensure ffmpeg process is terminated
                try:
                    process.terminate()
                except Exception:
                    pass
                print("Stopped streaming.")

        threading.Thread(target=stream_audio, daemon=True).start()

    def on_message(ws, message):
        try:
            data = json.loads(message)
            if data.get("type") == "Turn":
                transcript = data.get("transcript", "")
                print(f"\r{transcript}", end="")
        except Exception as e:
            print(f"Message error: {e}")

    def on_error(ws, error):
        print(f"\nWebSocket error: {error}")
        stop_event.set()

    def on_close(ws, code, msg):
        print(f"\nWebSocket closed: {code}, {msg}")
        stop_event.set()

    ws_app = websocket.WebSocketApp(
        API_ENDPOINT,
        header={"Authorization": API_KEY},
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    global live_running
    if live_running:
        # already running
        return None, None

    ws_thread = threading.Thread(target=ws_app.run_forever)
    ws_thread.daemon = True
    ws_thread.start()
    live_running = True

    return ws_app, ws_thread

@app.route("/live-transcribe", methods=["GET"])
def live_transcribe():
    """Endpoint to start live transcription."""
    ws_app, ws_thread = start_live_transcription()
    if ws_app is None:
        return jsonify({"status": "Live transcription already running."}), 400
    return jsonify({"status": "Live transcription started. Speak into your mic."})


@app.route('/live-stop', methods=['POST'])
def live_stop():
    """Endpoint to stop live transcription."""
    global live_running
    stop_event.set()
    live_running = False
    return jsonify({"status": "Stopping live transcription."})

# ------------------ PRE-RECORDED TRANSCRIPTION ------------------

def transcribe_file(audio_url: str):
    """Transcribe pre-recorded audio using AssemblyAI REST API."""
    data = {
        "audio_url": audio_url,
        "speech_model": "universal"
    }
    url = ASSEMBLYAI_BASE + "/v2/transcript"
    response = requests.post(url, json=data, headers={"authorization": API_KEY})
    transcript_id = response.json()['id']
    polling_endpoint = ASSEMBLYAI_BASE + "/v2/transcript/" + transcript_id

    while True:
        transcription_result = requests.get(polling_endpoint, headers={"authorization": API_KEY}).json()
        if transcription_result['status'] == 'completed':
            return transcription_result['text']
        elif transcription_result['status'] == 'error':
            raise RuntimeError(f"Transcription failed: {transcription_result['error']}")
        else:
            time.sleep(3)

@app.route("/file-transcribe", methods=["POST"])
def file_transcribe():
    """Endpoint to transcribe pre-recorded audio.

    Supports either JSON {audio_url} or a multipart file upload form field named 'file'.
    If a file is uploaded it will be forwarded to AssemblyAI's upload endpoint and the returned
    upload URL will be used for transcription.
    """
    audio_url = None
    print("/file-transcribe called")
    # JSON payload with audio_url
    if request.is_json:
        data = request.get_json()
        audio_url = data.get('audio_url')

    # Multipart file upload
    if 'file' in request.files:
        upload_file = request.files['file']
        print(f"Received uploaded file: {upload_file.filename}, size={len(upload_file.read())} bytes")
        # rewind stream since we read it for logging
        upload_file.stream.seek(0)
        try:
            upload_url = ASSEMBLYAI_BASE + '/v2/upload'
            headers = {'authorization': API_KEY}
            # send raw file bytes
            resp = requests.post(upload_url, data=upload_file.read(), headers=headers)
            resp.raise_for_status()
            upload_result = resp.json()
            # AssemblyAI's response usually contains an 'upload_url'
            audio_url = upload_result.get('upload_url') or upload_result.get('url')
            print(f"Upload result: {upload_result}")
        except Exception as e:
            return jsonify({'error': f'upload failed: {e}'}), 500

    if not audio_url:
        return jsonify({"error": "audio_url is required (or upload a file)"}), 400

    try:
        transcript_text = transcribe_file(audio_url)
        return jsonify({"transcript": transcript_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ RUN APP ------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
