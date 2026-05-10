import aria2p
import os
from typing import Optional, Dict

class DownloadManager:
    def __init__(self):
        host = os.getenv("ARIA2C_HOST", "http://localhost")
        if not host.startswith("http"):
            host = f"http://{host}"
            
        port = int(os.getenv("ARIA2C_PORT", "6800"))
        secret = os.getenv("ARIA2C_SECRET", "")
        
        self.api = aria2p.API(
            aria2p.Client(
                host=host,
                port=port,
                secret=secret
            )
        )

    def add_magnet(self, magnet_uri: str) -> Optional[str]:
        try:
            download = self.api.add_magnet(magnet_uri)
            return download.gid
        except Exception as e:
            print(f"Error adding magnet: {e}")
            return None

    def get_progress(self, gid: str) -> Optional[Dict[str, str]]:
        try:
            download = self.api.get_download(gid)
            
            # If it's a magnet link, it resolves metadata first then spawns a new GID
            if download.followed_by_ids:
                new_gid = download.followed_by_ids[0]
                download = self.api.get_download(new_gid)
                
            return {
                "gid": download.gid,
                "name": download.name,
                "status": download.status,
                "progress_string": download.progress_string(),
                "download_speed": download.download_speed_string(),
                "is_complete": download.is_complete
            }
        except Exception as e:
            print(f"Error getting progress: {e}")
            return None

    def remove_download(self, gid: str) -> bool:
        try:
            download = self.api.get_download(gid)
            self.api.remove([download], force=True, files=True, clean=True)
            return True
        except Exception as e:
            print(f"Error removing download: {e}")
            return False
