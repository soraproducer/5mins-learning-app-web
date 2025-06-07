#!/bin/bash
set -e

echo "Starting database reset..."
python3 -m db.db_manager --all

echo ""
echo "✅ Database reset complete"
echo "   Test User ID: 00000000-0000-0000-0000-000000000000"
echo "   Name: Test User"
