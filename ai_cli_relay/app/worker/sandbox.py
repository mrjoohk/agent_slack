import os
from typing import Optional

class SandboxMounter:
    """
    UF-03-A: Context Volume Mounter
    호스트의 workspace 경로를 Docker 컨테이너에 안전하게 마운트하고 
    권한(UID/GID)을 설정하는 역할을 담당합니다.
    """
    def __init__(self, workspace_path: str, write_permission: bool = False):
        self.workspace_path = workspace_path
        self.write_permission = write_permission

    def get_mount_config(self) -> dict:
        """
        Docker SDK의 volumes 인자에 들어갈 딕셔너리를 생성합니다.
        읽기전용(ro) / 쓰기전용(rw)을 구분합니다.
        """
        mode = 'rw' if self.write_permission else 'ro'
        return {
            self.workspace_path: {
                'bind': '/app/workspace',
                'mode': mode
            }
        }
        
    def get_user_spec(self) -> Optional[str]:
        """
        호스트 머신의 UID와 GID를 컨테이너 권한으로 주입하기 위한 문자열을 생성.
        윈도우 등 지원하지 않는 환경(AttributeError)은 None 반환 (Fallback).
        """
        try:
            uid = os.getuid()
            gid = os.getgid()
            return f"{uid}:{gid}"
        except AttributeError:
            # Fallback for Windows or unknown systems safely
            return None
