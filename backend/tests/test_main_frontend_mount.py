from importlib import reload
from pathlib import Path

import backend.main as main_module


def test_backend_does_not_mount_frontend_when_index_missing(monkeypatch):
    original_isdir = Path.is_dir
    original_isfile = Path.is_file

    def fake_isdir(self):
        if str(self).endswith("frontend/dist"):
            return True
        return original_isdir(self)

    def fake_isfile(self):
        if str(self).endswith("frontend/dist/index.html"):
            return False
        return original_isfile(self)

    monkeypatch.setattr(Path, "is_dir", fake_isdir)
    monkeypatch.setattr(Path, "is_file", fake_isfile)

    module = reload(main_module)
    mounted_paths = [getattr(route, "path", "") for route in module.app.routes]

    assert "/health" in mounted_paths
    assert "/" not in mounted_paths
