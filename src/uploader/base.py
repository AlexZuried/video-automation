class BaseUploader:
    def upload(self, video_path: str, metadata: dict) -> bool:
        raise NotImplementedError
