from core.llm import call_llm


def answer_question(question: str, transcripts: dict, video_titles: dict) -> str:
    """
    Answer a question based on video transcripts using RAG approach.
    
    Args:
        question: The user's question
        transcripts: Dictionary of {video_id: transcript_text}
        video_titles: Dictionary of {video_id: video_title}
    
    Returns:
        Answer based on the transcripts
    """
    # Prepare context from all transcripts
    context_parts = []
    for video_id, transcript in transcripts.items():
        title = video_titles.get(video_id, video_id)
        context_parts.append(f"=== Video: {title} ===\n{transcript}\n")
    
    full_context = "\n\n".join(context_parts)
    
    # Create prompt for the LLM
    prompt = f"""You are a helpful assistant that answers questions based on YouTube video transcripts.

Below are the transcripts from one or more YouTube videos:

{full_context}

Now answer the following question based ONLY on the information in the transcripts above:

Question: {question}

Instructions:
- Answer accurately based ONLY on the information in the provided transcripts
- If the answer is not in the transcripts, say "I don't have that information in the transcripts"
- Cite which video the information comes from when relevant
- Be concise but thorough
- If multiple videos cover the topic, synthesize information from all relevant sources

Answer:"""
    
    return call_llm(prompt)
