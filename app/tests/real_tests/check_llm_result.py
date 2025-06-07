import asyncio
import json
from app.services.llm_providers import LLMOrchestrator
from app.core.config import settings

# Create an orchestrator (will initialize providers with default settings)
orchestrator = LLMOrchestrator()

# Process a user query with the complete pipeline
async def handle_user_question(question: str, print_details: bool = True):
    """
    Process a user query and return both raw 3rd party LLM responses and the final analysis.
    
    Args:
        question: The user's question to ask the LLMs
        print_details: Whether to print detailed output during processing
        
    Returns:
        Dictionary containing both raw LLM responses and the final analysis
    """
    if print_details:
        print(f"\n🔍 Processing query: '{question}'")
        print("\n" + "="*80 + "\n")
    
    # Get the list of enabled providers from settings
    enabled_providers = settings.get_enabled_providers()
    if print_details:
        print(f"📊 Using providers: {', '.join(enabled_providers)}")
    
    # Get comprehensive analysis from multiple sources
    result = await orchestrator.process_query(
        query=question,
        system_prompt="You are an expert researcher providing comprehensive information.",
        providers=enabled_providers
    )
    
    # Print individual LLM responses if details are requested
    if print_details:
        print("\n" + "="*80)
        print("\n📝 INDIVIDUAL LLM RESPONSES:\n")
        
        # Define display names for providers
        display_names = {
            "openai": "ChatGPT",
            "claude": "Claude",
            "gemini": "Gemini"
        }
        
        # Check if we have any successful responses
        if not result.raw_responses:
            print("⚠️ No successful responses from any LLM providers")
            
        # Print any provider errors
        if hasattr(result, 'provider_errors') and result.provider_errors:
            print("\n⚠️ PROVIDER ERRORS:\n")
            for provider_name, error in result.provider_errors.items():
                display_name = display_names.get(provider_name, provider_name.capitalize())
                print(f"- {display_name}: {error}")
            print("\n" + "-"*50)
        
        # Print successful responses
        for provider_name, response in result.raw_responses.items():
            display_name = display_names.get(provider_name, provider_name.capitalize())
            
            print(f"\n## {display_name}\n")
            print(response.content)
            
            # Print metrics if available
            if response.metrics:
                metrics_str = ", ".join([f"{k}: {v}" for k, v in response.metrics.items() 
                                        if k != 'elapsed_time' and k != 'model'])
                print(f"\nMetrics: {metrics_str}")
                
                # Print model information if available
                if 'model' in response.metrics:
                    print(f"Model: {response.metrics['model']}")
                
                # Print elapsed time if available
                if 'elapsed_time' in response.metrics:
                    print(f"Time: {response.metrics['elapsed_time']:.2f}s")
            
            print("\n" + "-"*50)
        
        print("\n" + "="*80)
        print("\n🔄 OLLAMA SUMMARY ANALYSIS:\n")
        print(result.summary)
        print("\n" + "="*80 + "\n")
    
    # Return both raw responses and the final analysis
    return {
        # Include the original question
        "question": question,
        
        # Include raw responses from all 3rd party LLMs
        "raw_responses": {
            provider: {
                "content": response.content,
                "metrics": response.metrics,
                "timestamp": response.timestamp.isoformat()
            }
            for provider, response in result.raw_responses.items()
        },
        
        # Include provider errors if any
        "provider_errors": getattr(result, 'provider_errors', {}),
        
        # Include the final analysis
        "analysis": {
            "summary": result.summary,
            "consensus_items": result.consensus_items,
            "difference_items": result.difference_items,
            "confidence": result.confidence,
            "sources": result.sources
        }
    }

def print_json(data):
    """Print data as formatted JSON"""
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    # Example question to test the system
    # question = "Tell me the difference between DDPM and DDIM."
    question = "Tell me the difference between UI and UX."
    
    # Process the question and get both raw responses and analysis
    result = asyncio.run(handle_user_question(question))
    
    # If you want to see the data as JSON
    print_json(result)
