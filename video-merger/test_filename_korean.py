from werkzeug.utils import secure_filename
import time

filename_examples = [
    "동영상.mp4",
    "my video.mp4",
]

for name in filename_examples:
    secured = secure_filename(name)
    timestamp = int(time.time() * 1000)
    final = f"{timestamp:015d}_{secured}"
    print(f"Original: '{name}' -> Secured: '{secured}' -> Final: '{final}'")
