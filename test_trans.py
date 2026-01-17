from transcript_extractor import extract_transcript

url = "https://www.youtube.com/watch?v=f5Ihdw32tTw&t=1723s"

transcript = extract_transcript(url)

print("Transcript Length:", len(transcript))  # print length of the transcript
