import os
import heapq


def cleanup_old_images(directory: str, max_count: int):
    """删除超出数量的最旧图片"""
    if max_count <= 0:
        return

    with os.scandir(directory) as entries:
        files = [
            (entry.path, entry.stat().st_mtime)
            for entry in entries
            if entry.is_file() and entry.name.lower().endswith(('.jpg', '.png', '.jpeg'))
        ]

    if len(files) <= max_count:
        return

    to_keep = heapq.nsmallest(max_count, files, key=lambda x: x[1])
    keep_paths = {path for path, _ in to_keep}

    for path, _ in files:
        if path not in keep_paths:
            try:
                os.remove(path)
            except Exception as e:
                print(f"删除旧图片失败：{path}, {e}")
