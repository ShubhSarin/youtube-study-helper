from google.adk.agents import Agent

summary_agent = Agent(
    name="youtube_summary_agent",
    model="gemini-2.5-flash",
    description="Agent that summarizes YouTube transcripts into structured notes.",
    instruction="Summarizes YouTube transcripts into structured notes."
)

flashcard_agent = Agent(
    name="youtube_flashcard_agent",
    model="gemini-2.5-flash",
    description="Agent that generates flashcards from YouTube transcripts.",
    instruction="Generates flashcards from YouTube transcripts."
)

quiz_agent = Agent(
    name="youtube_quiz_agent",
    model="gemini-2.5-flash",
    description="Agent that generates quizzes from YouTube transcripts.",
    instruction="Generates quizzes from YouTube transcripts."
)

rag_agent = Agent(
    name="youtube_rag_agent",
    model="gemini-2.5-flash",
    description="Agent that answers questions based on YouTube video transcripts.",
    instruction="""You are a helpful assistant that answers questions based on YouTube video transcripts provided to you.
    
    Instructions:
    - Answer questions accurately based ONLY on the information in the provided transcripts
    - If the answer is not in the transcripts, say "I don't have that information in the transcripts"
    - Cite which video the information comes from when relevant
    - Be concise but thorough
    - If multiple videos cover the topic, synthesize information from all relevant sources"""
)
