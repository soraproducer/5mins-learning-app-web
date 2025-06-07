#!/usr/bin/env python3
"""
Script to test the delete functionality of conversations.
This script will:
1. Create some fake conversations in the database
2. Verify they exist
3. Test the delete functionality through the API
4. Verify they are deleted from the database
"""

import asyncio
import requests
import json
from datetime import datetime
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "00000000-0000-0000-0000-000000000000"

# Sample conversation topics for testing
SAMPLE_TOPICS = [
    "What is the difference between machine learning and deep learning?",
    "How does photosynthesis work in plants?", 
    "The history of the Roman Empire",
    "Explain quantum computing in simple terms",
    "What are the benefits of renewable energy?",
    "How do vaccines work to prevent diseases?",
    "The impact of social media on modern society",
    "Basic principles of economics and supply and demand"
]

def create_test_conversations():
    """Create several test conversations using the API"""
    print("Creating test conversations...")
    created_conversations = []
    
    for i, topic in enumerate(SAMPLE_TOPICS):
        try:
            # Create conversation
            conversation_data = {
                "user_id": TEST_USER_ID,
                "user_name": f"Test User {i+1}",
                "topic": topic
            }
            
            response = requests.post(
                f"{BASE_URL}/api/conversations",
                json=conversation_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                conversation = response.json()
                created_conversations.append(conversation)
                print(f"✓ Created conversation: {conversation['conversation_id']} - {topic[:50]}...")
            else:
                print(f"✗ Failed to create conversation: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"✗ Error creating conversation: {e}")
    
    return created_conversations

def get_user_conversations():
    """Get all conversations for the test user"""
    try:
        response = requests.get(f"{BASE_URL}/api/conversations/user/{TEST_USER_ID}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Failed to get conversations: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"✗ Error getting conversations: {e}")
        return []

def delete_conversation(conversation_id):
    """Delete a conversation using the API"""
    try:
        response = requests.delete(f"{BASE_URL}/api/conversations/{conversation_id}")
        if response.status_code == 204:
            return True
        else:
            print(f"✗ Failed to delete conversation {conversation_id}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error deleting conversation {conversation_id}: {e}")
        return False

def main():
    """Main test function"""
    print("=== Testing Conversation Delete Functionality ===\n")
    
    # Step 1: Create test conversations
    print("Step 1: Creating test conversations")
    created_conversations = create_test_conversations()
    print(f"Created {len(created_conversations)} conversations\n")
    
    # Step 2: Verify conversations exist
    print("Step 2: Verifying conversations exist in database")
    conversations = get_user_conversations()
    print(f"Found {len(conversations)} conversations in database")
    
    for conv in conversations[:3]:  # Show first 3
        print(f"  - {conv['conversation_id']}: {conv['topic'][:50]}...")
    
    if len(conversations) > 3:
        print(f"  ... and {len(conversations) - 3} more")
    print()
    
    # Step 3: Test delete functionality
    if conversations:
        print("Step 3: Testing delete functionality")
        
        # Delete the first conversation
        first_conversation = conversations[0]
        conversation_id = first_conversation['conversation_id']
        topic = first_conversation['topic']
        
        print(f"Attempting to delete: {conversation_id} - {topic[:50]}...")
        
        if delete_conversation(conversation_id):
            print(f"✓ Successfully deleted conversation {conversation_id}")
            
            # Verify it's gone
            updated_conversations = get_user_conversations()
            if len(updated_conversations) == len(conversations) - 1:
                print(f"✓ Verified: Conversation count reduced from {len(conversations)} to {len(updated_conversations)}")
                
                # Check that the specific conversation is gone
                remaining_ids = [c['conversation_id'] for c in updated_conversations]
                if conversation_id not in remaining_ids:
                    print(f"✓ Verified: Conversation {conversation_id} no longer exists in database")
                else:
                    print(f"✗ Error: Conversation {conversation_id} still exists in database!")
            else:
                print(f"✗ Error: Conversation count unchanged ({len(conversations)} -> {len(updated_conversations)})")
        else:
            print(f"✗ Failed to delete conversation {conversation_id}")
    else:
        print("No conversations found to test delete functionality")
    
    print("\n=== Test Complete ===")
    
    # Final summary
    final_conversations = get_user_conversations()
    print(f"Final conversation count: {len(final_conversations)}")

if __name__ == "__main__":
    main()
