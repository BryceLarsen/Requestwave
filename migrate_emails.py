#!/usr/bin/env python3

"""
MongoDB Email Normalization Migration

This script:
1. Backfills email_lc field with normalized (lowercase) emails
2. Creates unique index on email_lc field
3. Handles duplicate email conflicts
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv('/app/backend/.env')

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'test_database')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_emails():
    """Run email normalization migration"""
    logger.info('🚀 Starting email normalization migration...')
    logger.info(f'📍 MongoDB URL: {MONGO_URL}')
    logger.info(f'📍 Database: {DB_NAME}')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    musicians_collection = db.musicians
    
    try:
        # Step 1: Check current state
        total_musicians = await musicians_collection.count_documents({})
        with_email_lc = await musicians_collection.count_documents({"email_lc": {"$exists": True}})
        
        logger.info(f'📊 Total musicians: {total_musicians}')
        logger.info(f'📊 Already have email_lc: {with_email_lc}')
        
        # Step 2: Find potential duplicates before migration
        logger.info('🔍 Checking for potential duplicate emails...')
        duplicate_pipeline = [
            {
                "$group": {
                    "_id": {"$toLower": "$email"},
                    "count": {"$sum": 1},
                    "docs": {
                        "$push": {
                            "id": "$id",
                            "email": "$email", 
                            "name": "$name"
                        }
                    }
                }
            },
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicates = await musicians_collection.aggregate(duplicate_pipeline).to_list(None)
        
        if duplicates:
            logger.warning('⚠️  Found potential duplicate emails:')
            for dup in duplicates:
                logger.warning(f'   Email: {dup["_id"]} ({dup["count"]} accounts)')
                for doc in dup["docs"]:
                    logger.warning(f'     - ID: {doc["id"]}, Name: {doc["name"]}, Email: {doc["email"]}')
            logger.info('💡 You may want to use the Admin Panel to merge these accounts after migration.')
        
        # Step 3: Backfill email_lc field for documents that don't have it
        logger.info('🔄 Backfilling email_lc field...')
        backfill_result = await musicians_collection.update_many(
            {"email_lc": {"$exists": False}},
            [{"$set": {"email_lc": {"$toLower": "$email"}}}]
        )
        
        logger.info(f'✅ Backfilled {backfill_result.modified_count} documents')
        
        # Step 4: Create unique index (this will fail if there are actual duplicates)
        logger.info('🔐 Creating unique index on email_lc...')
        
        try:
            await musicians_collection.create_index(
                "email_lc", 
                unique=True, 
                name="unique_email_lc"
            )
            logger.info('✅ Successfully created unique index on email_lc')
        except Exception as index_error:
            if 'duplicate key' in str(index_error) or '11000' in str(index_error):
                logger.error('❌ Cannot create unique index due to duplicate emails!')
                logger.error('   Use the Admin Panel to merge duplicate accounts first.')
                
                # Show which emails are duplicated
                actual_duplicates = await musicians_collection.aggregate([
                    {
                        "$group": {
                            "_id": "$email_lc",
                            "count": {"$sum": 1},
                            "docs": {
                                "$push": {
                                    "id": "$id",
                                    "email": "$email",
                                    "name": "$name"
                                }
                            }
                        }
                    },
                    {"$match": {"count": {"$gt": 1}}}
                ]).to_list(None)
                
                logger.error('   Duplicate email_lc values:')
                for dup in actual_duplicates:
                    logger.error(f'     {dup["_id"]} ({dup["count"]} accounts)')
            else:
                raise index_error
        
        # Step 5: Final verification
        final_count = await musicians_collection.count_documents({"email_lc": {"$exists": True}})
        logger.info(f'📊 Final count with email_lc: {final_count}')
        
        # Check index status
        indexes = await musicians_collection.list_indexes().to_list(None)
        unique_email_index = None
        for idx in indexes:
            if idx.get('name') == 'unique_email_lc':
                unique_email_index = idx
                break
        
        if unique_email_index:
            logger.info('✅ Unique email index is active')
        else:
            logger.warning('⚠️  Unique email index not found - may need manual intervention')
        
        logger.info('🎉 Email normalization migration completed!')
        
    except Exception as error:
        logger.error(f'❌ Migration failed: {error}')
        raise
    finally:
        client.close()
        logger.info('🔌 Disconnected from MongoDB')

# Run migration if called directly
if __name__ == "__main__":
    asyncio.run(migrate_emails())