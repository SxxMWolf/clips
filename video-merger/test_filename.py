from werkzeug.utils import secure_filename
import time

filename_examples = [
    "test.mp4",
    "video.mp4",
    "VIDEO.MP4",
    "my video.mp4",
    "../../etc/passwd.mp4"
]

for name in filename_examples:
    secured = secure_filename(name)
    timestamp = int(time.time() * 1000)
    final = f"{timestamp:015d}_{secured}"
    print(f"Original: '{name}' -> Secured: '{secured}' -> Final: '{final}'")
