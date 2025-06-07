#!/usr/bin/env python3
"""
Database Visualization Tool

This script provides visualization and inspection of database tables
and relationships for the 5mins-learning-app.

Usage:
    python -m db.visualize_db [--table TABLE_NAME] [--limit N] [--format FORMAT]
    python -m db.visualize_db --conversation CONVERSATION_ID
    python -m db.visualize_db --user USER_ID
    python -m db.visualize_db --message MESSAGE_ID

Options:
    --table         Table name to view (users, conversations, messages, or all)
    --limit         Maximum number of records to display per table (default: 10)
    --format        Output format (text, json, or table) (default: table)
    --conversation  Display details of a specific conversation by ID
    --user          Display a specific user's conversations by ID
    --message       Display detailed information about a specific message by ID
"""
import sys
import asyncio
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import uuid

# Add project root to PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncpg
from tabulate import tabulate
from app.core.config import settings
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message

class DBVisualizer:
    """Database visualization and inspection tool"""
    
    def __init__(self, db_url: Optional[str] = None):
        """Initialize with optional custom database URL"""
        # Strip SQLAlchemy dialect for asyncpg compatibility
        self.db_url = db_url or settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
        self.conn = None
    
    async def connect(self):
        """Connect to the database"""
        self.conn = await asyncpg.connect(self.db_url)
        print(f"🔌 Connected to database: {self.db_url.split('/')[-1]}")
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            print("🔌 Connection closed")
    
    async def get_table_stats(self) -> Dict[str, int]:
        """Get count of records in each table"""
        tables = {'users': 0, 'conversations': 0, 'messages': 0}
        
        for table in tables.keys():
            query = f"SELECT COUNT(*) FROM {table}"
            count = await self.conn.fetchval(query)
            tables[table] = count
        
        return tables
    
    async def get_table_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get data from a specific table with limit"""
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        records = await self.conn.fetch(query)
        
        # Convert records to dictionaries and handle UUID serialization
        result = []
        for record in records:
            record_dict = dict(record)
            # Convert UUID to string for JSON serialization
            for key, value in record_dict.items():
                if isinstance(value, uuid.UUID):
                    record_dict[key] = str(value)
                elif isinstance(value, datetime):
                    record_dict[key] = value.isoformat()
            result.append(record_dict)
            
        return result
    
    async def get_conversation_with_messages(self, conversation_id: str, limit: int = 20) -> Dict[str, Any]:
        """Get a conversation with its messages"""
        # Get conversation details
        conv_query = """
            SELECT * FROM conversations 
            WHERE conversation_id = $1
        """
        conversation = await self.conn.fetchrow(conv_query, uuid.UUID(conversation_id))
        
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        # Get messages for the conversation
        msg_query = """
            SELECT * FROM messages 
            WHERE conversation_id = $1
            ORDER BY timestamp
            LIMIT $2
        """
        messages = await self.conn.fetch(msg_query, uuid.UUID(conversation_id), limit)
        
        # Format result
        result = dict(conversation)
        # Convert UUIDs to strings
        for key, value in result.items():
            if isinstance(value, uuid.UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
                
        # Format messages
        result['messages'] = []
        for msg in messages:
            msg_dict = dict(msg)
            for key, value in msg_dict.items():
                if isinstance(value, uuid.UUID):
                    msg_dict[key] = str(value)
                elif isinstance(value, datetime):
                    msg_dict[key] = value.isoformat()
            result['messages'].append(msg_dict)
            
        return result
    
    async def get_message_details(self, message_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific message"""
        # Get message details
        msg_query = """
            SELECT * FROM messages 
            WHERE message_id = $1
        """
        message = await self.conn.fetchrow(msg_query, uuid.UUID(message_id))
        
        if not message:
            raise ValueError(f"Message not found: {message_id}")
        
        # Convert to dictionary and handle special types
        result = dict(message)
        for key, value in result.items():
            if isinstance(value, uuid.UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
        
        # Get the conversation this message belongs to
        conv_query = """
            SELECT * FROM conversations 
            WHERE conversation_id = $1
        """
        conversation = await self.conn.fetchrow(conv_query, uuid.UUID(result['conversation_id']))
        
        if conversation:
            conv_data = dict(conversation)
            for key, value in conv_data.items():
                if isinstance(value, uuid.UUID):
                    conv_data[key] = str(value)
                elif isinstance(value, datetime):
                    conv_data[key] = value.isoformat()
            result['conversation'] = conv_data
        
        # Get parent message if available
        if result.get('parent_message_id'):
            parent_query = """
                SELECT * FROM messages 
                WHERE message_id = $1
            """
            parent_msg = await self.conn.fetchrow(parent_query, uuid.UUID(result['parent_message_id']))
            
            if parent_msg:
                parent_data = dict(parent_msg)
                for key, value in parent_data.items():
                    if isinstance(value, uuid.UUID):
                        parent_data[key] = str(value)
                    elif isinstance(value, datetime):
                        parent_data[key] = value.isoformat()
                result['parent_message'] = parent_data
        
        # Get child messages
        children_query = """
            SELECT * FROM messages 
            WHERE parent_message_id = $1
            ORDER BY timestamp
        """
        children = await self.conn.fetch(children_query, uuid.UUID(message_id))
        
        if children:
            children_data = []
            for child in children:
                child_dict = dict(child)
                for key, value in child_dict.items():
                    if isinstance(value, uuid.UUID):
                        child_dict[key] = str(value)
                    elif isinstance(value, datetime):
                        child_dict[key] = value.isoformat()
                children_data.append(child_dict)
            result['child_messages'] = children_data
        
        return result
    
    async def get_user_with_conversations(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get a user with their conversations"""
        # Get user details
        user_query = """
            SELECT * FROM users 
            WHERE user_id = $1
        """
        user = await self.conn.fetchrow(user_query, uuid.UUID(user_id))
        
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        # Get conversations for the user
        conv_query = """
            SELECT * FROM conversations 
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        conversations = await self.conn.fetch(conv_query, uuid.UUID(user_id), limit)
        
        # Format result
        result = dict(user)
        # Convert UUIDs to strings
        for key, value in result.items():
            if isinstance(value, uuid.UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
                
        # Format conversations
        result['conversations'] = []
        for conv in conversations:
            conv_dict = dict(conv)
            for key, value in conv_dict.items():
                if isinstance(value, uuid.UUID):
                    conv_dict[key] = str(value)
                elif isinstance(value, datetime):
                    conv_dict[key] = value.isoformat()
            result['conversations'].append(conv_dict)
            
        return result
    
    async def display_table_stats(self):
        """Display table statistics"""
        stats = await self.get_table_stats()
        
        print("\n📊 DATABASE STATISTICS")
        print("-" * 40)
        total = sum(stats.values())
        
        headers = ["Table", "Records", "% of DB"]
        rows = []
        
        for table, count in stats.items():
            percentage = (count / total * 100) if total > 0 else 0
            rows.append([table, count, f"{percentage:.1f}%"])
        
        print(tabulate(rows, headers=headers, tablefmt="pretty"))
        print(f"Total records: {total}")
    
    async def display_table_data(self, table_name: str, limit: int = 10, format: str = "table"):
        """Display data from a table in specified format"""
        if table_name not in ['users', 'conversations', 'messages', 'all']:
            print(f"❌ Invalid table name: {table_name}")
            print("Valid tables: users, conversations, messages, all")
            return
        
        if table_name == 'all':
            tables = ['users', 'conversations', 'messages']
        else:
            tables = [table_name]
        
        for table in tables:
            data = await self.get_table_data(table, limit)
            
            if not data:
                print(f"\n📋 Table '{table}' is empty")
                continue
                
            print(f"\n📋 TABLE: {table.upper()} (showing {len(data)} of {await self.conn.fetchval(f'SELECT COUNT(*) FROM {table}')} records)")
            print("-" * 80)
            
            if format == "json":
                print(json.dumps(data, indent=2))
            elif format == "table":
                # Extract headers from the first record
                headers = list(data[0].keys())
                rows = []
                
                for record in data:
                    row = []
                    for header in headers:
                        value = record[header]
                        # Truncate long values
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:47] + "..."
                        row.append(value)
                    rows.append(row)
                
                print(tabulate(rows, headers=headers, tablefmt="pretty"))
            else:
                # Simple text format
                for i, record in enumerate(data):
                    print(f"\nRecord {i+1}:")
                    for key, value in record.items():
                        print(f"  {key}: {value}")
                    print()
    
    async def display_conversation_tree(self, conversation_id: str):
        """Display a conversation with its messages in a tree structure"""
        try:
            data = await self.get_conversation_with_messages(conversation_id)
            
            print(f"\n🔍 CONVERSATION: {data['conversation_id']}")
            print("-" * 80)
            print(f"Topic: {data['topic']}")
            print(f"User: {data['user_name']} ({data['user_id']})")
            print(f"Created: {data['created_at']}")
            print(f"Updated: {data['updated_at']}")
            print(f"Messages: {len(data['messages'])}")
            print("-" * 80)
            
            if not data['messages']:
                print("No messages in this conversation")
                return
            
            print("\n📝 MESSAGES:")
            for i, msg in enumerate(data['messages']):
                # Set emoji based on role
                if msg['role'] == 'user':
                    emoji = "👤"
                elif msg['role'] == 'assistant':
                    emoji = "🤖"
                elif msg['role'] == 'system':
                    emoji = "⚙️"
                else:
                    emoji = "📄"
                    
                print(f"\n{emoji} {msg['role'].upper()}: {msg['message_id']}")
                print(f"   Time: {msg['timestamp']}")
                
                # Truncate content for display
                content = msg['content']
                if len(content) > 100:
                    content = content[:97] + "..."
                print(f"   Content: {content}")
                
                # Show LLM info if available
                if msg['llm_id']:
                    print(f"   LLM: {msg['llm_id']}")
                
                # Show parent message if available
                if msg['parent_message_id']:
                    print(f"   Parent: {msg['parent_message_id']}")
        
        except ValueError as e:
            print(f"❌ Error: {e}")
    
    async def display_message_details(self, message_id: str):
        """Display detailed information about a specific message"""
        try:
            data = await self.get_message_details(message_id)
            
            # Set emoji based on role
            if data['role'] == 'user':
                emoji = "👤"
            elif data['role'] == 'assistant':
                emoji = "🤖"
            elif data['role'] == 'system':
                emoji = "⚙️"
            else:
                emoji = "📄"
            
            print(f"\n{emoji} MESSAGE: {data['message_id']}")
            print("-" * 80)
            print(f"Role: {data['role']}")
            print(f"Time: {data['timestamp']}")
            print(f"Conversation ID: {data['conversation_id']}")
            
            if data.get('llm_id'):
                print(f"LLM: {data['llm_id']}")
                
            if data.get('llm_metadata') and data['llm_metadata'] is not None:
                # Handle metadata which might be JSON or a string
                if isinstance(data['llm_metadata'], str):
                    try:
                        metadata = json.loads(data['llm_metadata'])
                        print(f"LLM Metadata:")
                        for key, value in metadata.items():
                            print(f"   {key}: {value}")
                    except json.JSONDecodeError:
                        print(f"LLM Metadata: {data['llm_metadata']}")
                else:
                    print(f"LLM Metadata: {data['llm_metadata']}")
                
            if data.get('parent_message_id'):
                print(f"Parent Message ID: {data['parent_message_id']}")
            
            print("-" * 80)
            print(f"Content:\n{data['content']}")
            print("-" * 80)
            
            # Show conversation information
            if data.get('conversation'):
                conv = data['conversation']
                print(f"\n💬 CONVERSATION CONTEXT:")
                print(f"Topic: {conv['topic']}")
                print(f"User: {conv['user_name']} ({conv['user_id']})")
                print(f"Created: {conv['created_at']}")
                print(f"Updated: {conv['updated_at']}")
            
            # Show parent message if available
            if data.get('parent_message'):
                parent = data['parent_message']
                parent_emoji = "👤" if parent['role'] == 'user' else ("🤖" if parent['role'] == 'assistant' else "⚙️")
                
                print(f"\n↑ PARENT MESSAGE ({parent_emoji} {parent['role']}):")
                content = parent['content']
                if len(content) > 100:
                    content = content[:97] + "..."
                print(f"Content: {content}")
            
            # Show child messages if available
            if data.get('child_messages'):
                print(f"\n↓ CHILD MESSAGES ({len(data['child_messages'])}):")
                for i, child in enumerate(data['child_messages']):
                    child_emoji = "👤" if child['role'] == 'user' else ("🤖" if child['role'] == 'assistant' else "⚙️")
                    print(f"\n{i+1}. {child_emoji} {child['role']} ({child['message_id']})")
                    print(f"   Time: {child['timestamp']}")
                    
                    content = child['content']
                    if len(content) > 100:
                        content = content[:97] + "..."
                    print(f"   Content: {content}")
        
        except ValueError as e:
            print(f"❌ Error: {e}")
    
    async def display_user_conversations(self, user_id: str, limit: int = 10):
        """Display a user with their conversations"""
        try:
            data = await self.get_user_with_conversations(user_id, limit)
            
            print(f"\n👤 USER: {data['user_name']} ({data['user_id']})")
            print("-" * 80)
            print(f"Created: {data['created_at']}")
            print(f"Updated: {data['updated_at']}")
            print(f"Conversations: {len(data['conversations'])}")
            print("-" * 80)
            
            if not data['conversations']:
                print("No conversations for this user")
                return
            
            print("\n💬 CONVERSATIONS:")
            for i, conv in enumerate(data['conversations']):
                print(f"\n{i+1}. {conv['conversation_id']}")
                print(f"   Topic: {conv['topic']}")
                print(f"   Created: {conv['created_at']}")
                
                # Get message count
                msg_count = await self.conn.fetchval(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id = $1",
                    uuid.UUID(conv['conversation_id'])
                )
                print(f"   Messages: {msg_count}")
        
        except ValueError as e:
            print(f"❌ Error: {e}")


async def main():
    """Main entry point for the visualization tool"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Database visualization tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--table", choices=["users", "conversations", "messages", "all"], 
                      default="all", help="Table to visualize")
    parser.add_argument("--limit", type=int, default=10,
                      help="Maximum number of records to display")
    parser.add_argument("--format", choices=["text", "json", "table"],
                      default="table", help="Output format")
    parser.add_argument("--conversation", type=str,
                      help="Display a specific conversation by ID")
    parser.add_argument("--user", type=str,
                      help="Display a specific user's conversations by ID")
    parser.add_argument("--message", type=str,
                      help="Display detailed information about a specific message by ID")
    
    args = parser.parse_args()
    
    # Create visualizer and connect to database
    visualizer = DBVisualizer()
    await visualizer.connect()
    
    try:
        # Show overall database stats
        await visualizer.display_table_stats()
        
        # Handle specific viewing modes
        if args.message:
            await visualizer.display_message_details(args.message)
        elif args.conversation:
            await visualizer.display_conversation_tree(args.conversation)
        elif args.user:
            await visualizer.display_user_conversations(args.user, args.limit)
        else:
            # Display table data based on arguments
            await visualizer.display_table_data(args.table, args.limit, args.format)
        
    finally:
        # Close connection
        await visualizer.close()


if __name__ == "__main__":
    asyncio.run(main())
