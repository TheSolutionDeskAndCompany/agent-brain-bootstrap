import os
import argparse
import logging
from agent.memory.wp_client import get_latest_brain_post
from agent.decision_engine import respond
from agent.speech.voice_loop import run_voice_loop, AssemblyAIClient
from agent.utils.logger import get_logger

log = get_logger("agent_main")

def generate_text(user_text: str) -> str:
    """Generate a response to the user's input using the decision engine."""
    try:
        brain = get_latest_brain_post()
        mood = (brain.get("acf") or {}).get("agent_emotions")
        persona = (brain.get("acf") or {}).get("agent_personality")
        return respond(user_text, mood=mood, persona=persona)
    except Exception as e:
        log.error(f"Error generating response: {e}", exc_info=True)
        return f"I encountered an error: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='Agent Brain - Voice Interface')
    parser.add_argument('--device', type=int, default=None,
                      help='Audio device index (use list_devices.py to find)')
    parser.add_argument('--threshold', type=int, default=600,
                      help='Voice activation threshold (default: 600)')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Check for AssemblyAI API key
    if not os.getenv("ASSEMBLYAI_API_KEY"):
        log.error("ASSEMBLYAI_API_KEY environment variable not set")
        print("\nError: ASSEMBLYAI_API_KEY environment variable is required.")
        print("Please set it in your .env file or environment variables.")
        print("You can get a free API key at https://app.assemblyai.com/signup")
        return
    
    try:
        log.info("Starting agent in auto mode (no PTT required)")
        log.info("Speak to interact with the agent")
        log.info("Press Ctrl+C to exit")
        
        run_voice_loop(
            generate_text=generate_text,
            device=args.device,
            threshold=args.threshold
        )
        
    except KeyboardInterrupt:
        log.info("Shutting down...")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
