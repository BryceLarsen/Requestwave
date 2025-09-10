#!/usr/bin/env node

/**
 * MongoDB Email Normalization Migration
 * 
 * This script:
 * 1. Backfills email_lc field with normalized (lowercase) emails
 * 2. Creates unique index on email_lc field
 * 3. Handles duplicate email conflicts
 */

const { MongoClient } = require('mongodb');
require('dotenv').config();

const MONGO_URL = process.env.MONGO_URL || 'mongodb://localhost:27017/requestwave_production';

async function migrateEmails() {
  console.log('🚀 Starting email normalization migration...');
  console.log('📍 MongoDB URL:', MONGO_URL);
  
  const client = new MongoClient(MONGO_URL);
  
  try {
    await client.connect();
    console.log('✅ Connected to MongoDB');
    
    const db = client.db();
    const musiciansCollection = db.collection('musicians');
    
    // Step 1: Check current state
    const totalMusicians = await musiciansCollection.countDocuments();
    const withEmailLc = await musiciansCollection.countDocuments({ email_lc: { $exists: true } });
    
    console.log(`📊 Total musicians: ${totalMusicians}`);
    console.log(`📊 Already have email_lc: ${withEmailLc}`);
    
    // Step 2: Find potential duplicates before migration
    console.log('🔍 Checking for potential duplicate emails...');
    const duplicateCheck = await musiciansCollection.aggregate([
      {
        $group: {
          _id: { $toLower: "$email" },
          count: { $sum: 1 },
          docs: { $push: { id: "$_id", email: "$email", name: "$name" } }
        }
      },
      { $match: { count: { $gt: 1 } } }
    ]).toArray();
    
    if (duplicateCheck.length > 0) {
      console.log('⚠️  Found potential duplicate emails:');
      duplicateCheck.forEach(dup => {
        console.log(`   Email: ${dup._id} (${dup.count} accounts)`);
        dup.docs.forEach(doc => {
          console.log(`     - ID: ${doc.id}, Name: ${doc.name}, Email: ${doc.email}`);
        });
      });
      console.log('💡 You may want to use the Admin Panel to merge these accounts after migration.');
    }
    
    // Step 3: Backfill email_lc field for documents that don't have it
    console.log('🔄 Backfilling email_lc field...');
    const backfillResult = await musiciansCollection.updateMany(
      { email_lc: { $exists: false } },
      [{ $set: { email_lc: { $toLower: "$email" } } }]
    );
    
    console.log(`✅ Backfilled ${backfillResult.modifiedCount} documents`);
    
    // Step 4: Create unique index (this will fail if there are actual duplicates)
    console.log('🔐 Creating unique index on email_lc...');
    
    try {
      await musiciansCollection.createIndex(
        { email_lc: 1 }, 
        { unique: true, name: "unique_email_lc" }
      );
      console.log('✅ Successfully created unique index on email_lc');
    } catch (indexError) {
      if (indexError.code === 11000) {
        console.error('❌ Cannot create unique index due to duplicate emails!');
        console.error('   Use the Admin Panel to merge duplicate accounts first.');
        
        // Show which emails are duplicated
        const actualDuplicates = await musiciansCollection.aggregate([
          {
            $group: {
              _id: "$email_lc",
              count: { $sum: 1 },
              docs: { $push: { id: "$_id", email: "$email", name: "$name" } }
            }
          },
          { $match: { count: { $gt: 1 } } }
        ]).toArray();
        
        console.error('   Duplicate email_lc values:');
        actualDuplicates.forEach(dup => {
          console.error(`     ${dup._id} (${dup.count} accounts)`);
        });
        
      } else {
        throw indexError;
      }
    }
    
    // Step 5: Final verification
    const finalCount = await musiciansCollection.countDocuments({ email_lc: { $exists: true } });
    console.log(`📊 Final count with email_lc: ${finalCount}`);
    
    // Check index status
    const indexes = await musiciansCollection.indexes();
    const uniqueEmailIndex = indexes.find(idx => idx.name === 'unique_email_lc');
    
    if (uniqueEmailIndex) {
      console.log('✅ Unique email index is active');
    } else {
      console.log('⚠️  Unique email index not found - may need manual intervention');
    }
    
    console.log('🎉 Email normalization migration completed!');
    
  } catch (error) {
    console.error('❌ Migration failed:', error);
    process.exit(1);
  } finally {
    await client.close();
    console.log('🔌 Disconnected from MongoDB');
  }
}

// Run migration if called directly
if (require.main === module) {
  migrateEmails()
    .then(() => process.exit(0))
    .catch(error => {
      console.error('💥 Fatal error:', error);
      process.exit(1);
    });
}

module.exports = { migrateEmails };