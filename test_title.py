from core.youtube_utils import get_video_title

# Test with a known video ID
test_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
print(f"Testing video ID: {test_id}")
title = get_video_title(test_id)
print(f"Title: {title}")
