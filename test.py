from core.process import process_youtube_url

url = "https://www.youtube.com/playlist?list=PLZHQObOWTQDNU6R1_67000Dx_ZCJB-3pi"

results = process_youtube_url(url)

for vid, data in results.items():
    print(f"\n===== VIDEO {vid} =====")
    print(data["summary"][:500])
