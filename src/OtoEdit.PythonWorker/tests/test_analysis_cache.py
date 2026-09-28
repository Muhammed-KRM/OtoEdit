import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from services.analysis_cache import AnalysisCacheService


def test_compute_video_hash():
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"SAMPLE VIDEO DATA FOR HASHING TEST 1234567890")
        f.flush()
        temp_path = f.name

    try:
        hash1 = AnalysisCacheService.compute_video_hash(temp_path)
        hash2 = AnalysisCacheService.compute_video_hash(temp_path)
        assert len(hash1) == 64
        assert hash1 == hash2

        # Değişiklik yapıldığında hash değişmeli
        with open(temp_path, "ab") as f:
            f.write(b"EXTRA CONTENT")
        hash3 = AnalysisCacheService.compute_video_hash(temp_path)
        assert hash1 != hash3
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_compute_video_hash_non_existent():
    with pytest.raises(FileNotFoundError):
        AnalysisCacheService.compute_video_hash("/non/existent/path/video.mp4")


def test_analysis_cache_set_and_get():
    mock_redis = MagicMock()
    mock_redis.get.return_value = '{"project_id": "p1", "cuts": []}'
    mock_redis.set.return_value = True

    cache = AnalysisCacheService()
    cache._client = mock_redis

    edl = cache.get_cached_edl("dummy_hash_123")
    assert edl is not None
    assert edl["project_id"] == "p1"
    mock_redis.get.assert_called_with("otoedit:analysis:edl:dummy_hash_123")

    success = cache.set_cached_edl("dummy_hash_123", {"project_id": "p1", "cuts": []})
    assert success is True
    mock_redis.set.assert_called_once()


def test_analysis_cache_redis_unavailable_fail_safe():
    cache = AnalysisCacheService(host="127.0.0.1", port=59999)
    cache._client = None
    with patch.object(cache, "_get_client", return_value=None):
        # Redis çökerse veya yoksa uygulama patlamamalı, None / False dönmeli
        assert cache.get_cached_edl("any_hash") is None
        assert cache.set_cached_edl("any_hash", {"dummy": 1}) is False
