import subprocess
import os

class UploadManager:
    def __init__(self):
        self.rclone_remote = os.getenv("RCLONE_REMOTE", "gdrive:/Media")
        self.downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")

    def upload_file(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist.")
            return False
            
        try:
            cmd = [
                "rclone", "move", file_path, self.rclone_remote,
                "--delete-empty-src-dirs", "--ignore-existing"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Rclone output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Rclone failed with code {e.returncode}: {e.stderr}")
            return False
        except Exception as e:
            print(f"Upload error: {e}")
            return False

    def cleanup_empty_dirs(self):
        try:
            for root, dirs, files in os.walk(self.downloads_dir, topdown=False):
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except OSError:
                        pass
        except Exception as e:
            print(f"Cleanup error: {e}")
