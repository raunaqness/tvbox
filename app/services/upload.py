import asyncio
import os
import shutil

class UploadManager:
    def __init__(self):
        self.rclone_remote = os.getenv("RCLONE_REMOTE", "gdrive:/Media")
        self.downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")

    async def upload_file(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist.")
            return False
            
        try:
            target_path = f"{self.rclone_remote}/{os.path.basename(file_path)}"
            
            cmd = [
                "rclone", "move", file_path, target_path,
                "--delete-empty-src-dirs", "--ignore-existing"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print(f"Rclone output: {stdout.decode()}")
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                except Exception as del_e:
                    print(f"Failed to delete local path {file_path}: {del_e}")
                return True
            else:
                print(f"Rclone failed with code {process.returncode}: {stderr.decode()}")
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
