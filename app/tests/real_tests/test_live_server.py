#!/usr/bin/env python3
"""
INTEGRATION TEST WITH LIVE SERVER

THIS IS THE RECOMMENDED APPROACH for testing with background tasks and
async database operations in FastAPI applications.

INSTRUCTIONS:
1. First run the API server in a separate terminal window:
   uvicorn app.main:app --reload

2. Then run this test in another terminal:
   python -m app.tests.real_tests.test_live_server

This approach properly handles event loop issues by testing against a real
running server rather than using FastAPI's TestClient.
"""
import asyncio
import uuid
import httpx
import time
from pprint import pprint

# Server URL (change if needed)
BASE_URL = "http://localhost:8000"

# Fixed test user ID
TEST_USER_ID = "00000000-0000-0000-0000-000000000000"

# Test conversation topic (first question)
# TEST_TOPIC = "Explain the differences between PPO and GPRO in reinforcement learning"
TEST_TOPIC = "Why are Abyssinian cats very affectionate while some other cats are not?"

# Test follow-up question for the conversation
# TEST_FOLLOWUP_QUESTION = "Can you explain the advantages of PPO in more detail?"
TEST_FOLLOWUP_QUESTION = "Are Norwegian Forest cats affectionate?"

async def test_create_conversation():
    """Test creating a new conversation via the API"""
    # Conversation data
    conversation_data = {
        "topic": TEST_TOPIC,
        "user_id": TEST_USER_ID,
        "user_name": "Test User"
    }
    
    # Make the API request
    print(f"\n🔍 Creating conversation for topic: '{conversation_data['topic']}'")
    print("\n" + "="*80 + "\n")
    
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await client.post("/api/conversations", json=conversation_data)
        
        # Validate response
        assert response.status_code == 201, f"Expected status code 201, got {response.status_code}"
        
        conversation = response.json()
        print(f"✅ Conversation created successfully")
        print(f"📌 Conversation ID: {conversation['conversation_id']}")
        print(f"👤 User: {conversation['user_name']} (ID: {conversation['user_id']})")
        print(f"📝 Topic: {conversation['topic']}")
        print(f"⏰ Created at: {conversation['created_at']}")
        
        return conversation


async def test_first_reply(conversation_id, providers=None, local_model_id=None):
    """Test triggering the first reply for a conversation via the API"""
    print("\n" + "="*80)
    print(f"\n🔄 Requesting first reply for conversation: {conversation_id}")
    
    # Prepare request data
    request_data = {}
    if providers or local_model_id:
        request_data = {
            "providers": providers or ["openai", "claude", "gemini"],
            "local_model_id": local_model_id or "gemma3:12b"
        }
        print(f"📊 Using providers: {', '.join(request_data.get('providers', []))}")
        print(f"🤖 Using local model: {request_data.get('local_model_id')}")
    
    # Make the API request to trigger the first reply
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await client.post(f"/api/conversations/{conversation_id}/first-reply", 
                               json=request_data if request_data else None)
        
        # Validate response
        assert response.status_code == 202, f"Expected status code 202, got {response.status_code}"
        print(f"✅ First reply task initiated: {response.json()}")
        print("\n" + "="*80)
        
        return response.json()


async def test_conversation_reply(conversation_id, message_content, providers=None, local_model_id=None):
    """Test triggering a follow-up reply for a conversation via the API"""
    print("\n" + "="*80)
    print(f"\n🔄 Requesting follow-up reply for conversation: {conversation_id}")
    print(f"📝 Message: '{message_content}'")
    
    # Prepare request data
    request_data = {
        "message_content": message_content,
        "providers": providers or ["openai", "claude", "gemini"],
        "local_model_id": local_model_id or "gemma3:12b"
    }
    
    print(f"📊 Using providers: {', '.join(request_data.get('providers', []))}")
    print(f"🤖 Using local model: {request_data.get('local_model_id')}")
    
    # Make the API request to trigger the follow-up reply
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await client.post(f"/api/conversations/{conversation_id}/reply", 
                               json=request_data)
        
        # Validate response
        assert response.status_code == 202, f"Expected status code 202, got {response.status_code}"
        print(f"✅ Follow-up reply task initiated: {response.json()}")
        print("\n" + "="*80)
        
        return response.json()


async def poll_for_messages(conversation_id, max_attempts=24, delay_seconds=5, exclude_message_ids=None):
    """
    Poll for messages to appear
    
    Args:
        conversation_id: ID of the conversation to poll
        max_attempts: Maximum number of polling attempts
        delay_seconds: Delay between polling attempts
        exclude_message_ids: Optional list of message IDs to exclude (used to ignore already seen messages)
    """
    print(f"\n⏱️ Polling for message (max {max_attempts} attempts, {delay_seconds}s delay)")
    
    # Initialize empty set if None was provided
    exclude_message_ids = set(exclude_message_ids or [])
    
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        for attempt in range(max_attempts):
            await asyncio.sleep(delay_seconds)
            print(f"🔍 Checking for messages (attempt {attempt + 1}/{max_attempts})...")
            
            # Get messages for the conversation
            response = await client.get(f"/api/conversations/{conversation_id}/messages")
            
            if response.status_code != 200:
                print(f"⚠️ Error getting messages: {response.status_code}")
                continue
            
            messages = response.json()
            
            # Extract all assistant messages from the threaded structure
            assistant_messages = []
            def extract_assistant_messages(msg_list):
                for msg in msg_list:
                    if msg["role"] == "assistant" and msg["message_id"] not in exclude_message_ids:
                        assistant_messages.append(msg)
                    # Process replies if they exist
                    if msg.get("replies"):
                        extract_assistant_messages(msg["replies"])
            
            # Process all root messages
            extract_assistant_messages(messages)
            
            if assistant_messages:
                # Found the response! Sort by timestamp to get the latest message
                sorted_messages = sorted(assistant_messages, key=lambda m: m["timestamp"], reverse=True)
                message = sorted_messages[0]  # Get the latest message
                print("\n" + "="*80)
                print("\n🎉 RESPONSE RECEIVED:")
                print("\n" + "="*80 + "\n")
                print(message["content"])
                print("\n" + "="*80)
                
                # Print metadata if available
                if message.get("llm_metadata"):
                    print("\n📊 LLM METADATA:")
                    print("-"*50)
                    metadata = message["llm_metadata"]
                    
                    # Print sources used
                    if "sources" in metadata:
                        print(f"\nSources used: {', '.join(metadata['sources'])}")
                    
                    # Print confidence
                    if "confidence" in metadata:
                        print(f"Confidence: {metadata['confidence']}")
                        
                    # Print consensus items
                    if "consensus_items" in metadata and metadata["consensus_items"]:
                        print("\nConsensus items:")
                        for item in metadata["consensus_items"]:
                            print(f"- {item}")
                            
                    # Print difference items
                    if "difference_items" in metadata and metadata["difference_items"]:
                        print("\nDifference items:")
                        for item in metadata["difference_items"]:
                            print(f"- {item}")
                    
                    print("\n" + "="*80 + "\n")
                
                return message
            
            # Check for system error messages (also traverse the thread structure)
            system_messages = []
            def extract_system_messages(msg_list):
                for msg in msg_list:
                    if msg["role"] == "system":
                        system_messages.append(msg)
                    # Process replies if they exist
                    if msg.get("replies"):
                        extract_system_messages(msg["replies"])
            
            # Process all root messages for system messages
            extract_system_messages(messages)
            if system_messages:
                print("\n⚠️ SYSTEM MESSAGE:")
                print(system_messages[0]["content"])
                return system_messages[0]
        
        print("\n❌ Timed out waiting for a response")
        return None


async def run_full_integration_test():
    """Run the complete conversation flow including first reply and follow-up question"""
    print("\n" + "="*40)
    print("🧪 INTEGRATION TEST AGAINST LIVE SERVER")
    print("="*40 + "\n")
    
    print(f"⚠️  Ensure the server is running: uvicorn app.main:app --reload")
    print(f"📡 Testing against: {BASE_URL}")
    
    try:
        # Step 1: Create a conversation
        conversation = await test_create_conversation()
        conversation_id = conversation["conversation_id"]
        
        # Step 2: Request the first reply
        await test_first_reply(
            conversation_id=conversation_id,
            providers=["openai", "claude", "gemini"],
            local_model_id="gemma3:12b"
        )
        
        # Step 3: Poll for the first message to appear
        first_message = await poll_for_messages(conversation_id)
        
        if not first_message:
            print("\n⚠️ First message not received - timeout")
            return
            
        if first_message["role"] != "assistant":
            print(f"\n⚠️ Received {first_message['role']} message instead of assistant: {first_message['content']}")
            return
            
        print("\n✅ First reply received successfully!")
        
        # Step 4: Send a follow-up question
        print(f"\n📝 Sending follow-up question: '{TEST_FOLLOWUP_QUESTION}'")
        await test_conversation_reply(
            conversation_id=conversation_id,
            message_content=TEST_FOLLOWUP_QUESTION,
            providers=["openai", "claude", "gemini"],
            local_model_id="gemma3:12b"
        )
        
        # Step 5: Poll for the follow-up response, excluding the first message
        print("\n📝 Waiting for follow-up response...")
        follow_up_message = await poll_for_messages(
            conversation_id=conversation_id,
            exclude_message_ids=[first_message["message_id"]]
        )
        
        if follow_up_message:
            print("\n✅ Full conversation flow completed successfully!")
            if follow_up_message["role"] == "assistant":
                print("✅ Received follow-up assistant message")
            else:
                print(f"⚠️ Received {follow_up_message['role']} message: {follow_up_message['content']}")
        else:
            print("\n⚠️ Follow-up response not received - timeout")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_full_integration_test())
